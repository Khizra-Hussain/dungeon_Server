from fastapi import APIRouter, HTTPException, Header, WebSocket, WebSocketDisconnect
from db.database import SessionLocal
from models.world import World
from datetime import datetime  
from models.game import GameSession
from routes.auth_routes import verify_token
from models_pydantic import ActionRequest
from game_logic import active_games, active_worlds, validate_action, apply_action
import webSockets as ws_manager
import uuid
import json
import os

router = APIRouter(prefix="/games")

#create gamesession
@router.post("/")
def create_game(world_id: str, authorization: str = Header(...)):
    claims = verify_token(authorization)

    db = SessionLocal()
    try:
        world = db.query(World).filter(World.id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        if not os.path.exists(world.file_path):
            raise HTTPException(status_code=404, detail="World file not found on disk")

        
        with open(world.file_path) as f:
            world_data = json.load(f)

        game_id = str(uuid.uuid4())
        state_path = f"data/gameStates/state_{game_id}.json"

        # har entity ko unique id do is session ke liye
        entities = [
            {**e, "id": str(uuid.uuid4())}
            for e in world_data.get("entities", [])
        ]

        game_state = {
            "game_id": game_id,
            "world_id": world_id,
            "world_version": world.version,
            "status": "waiting", 
            "players": [],
            "entities": entities,
            "chat": []
        }

        #save in memory 
        active_games[game_id] = game_state
        active_worlds[game_id] = world_data

        os.makedirs("data/gameStates", exist_ok=True)
        with open(state_path, "w") as f:
            json.dump(game_state, f)

        session = GameSession(
            id=game_id,
            world_id=world_id,
            world_version=world.version,
            status="waiting",
            state_path=state_path
        )
        db.add(session)

        db.commit()

        return {"message": "game created", "game_id": game_id}
    finally:
        db.close()

# join game

@router.post("/{game_id}/join")
def join_game(game_id: str, authorization: str = Header(...)):
    
    claims = verify_token(authorization)

    game = active_games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    username = claims["username"]

    already_in = any(p["username"] == username for p in game["players"])
    if already_in:
        raise HTTPException(status_code=400, detail="Already in this game")

    # check max players
    world_data = active_worlds.get(game_id, {})
    # max players ke baad kisi ko allow mat karo
    if len(game["players"]) >= world_data.get("max_players", 4):
        raise HTTPException(status_code=400, detail="Game is full")


    # spawn point 0,0
    
    game["players"].append({
        "username": username,
        "x": 0,
        "y": 0,
        "spawn_x": 0,
        "spawn_y": 0,
        "has_moved": False,
        "hp": 10,
        "score": 0,
        "has_key": False
    })

    if len(game["players"]) == world_data.get("max_players", 4):
        game["status"] = "active"

    # play_count +1
    db = SessionLocal()
    try:
        world = db.query(World).filter(
            World.id == game["world_id"]
        ).first()
        if world:
            world.players_count = (world.players_count or 0) + 1
            db.commit()
    finally:
        db.close()

    return {"message": "joined game", "game_id": game_id}


@router.post("/{game_id}/action")
async def submit_action(game_id: str, action: ActionRequest,
                        authorization: str = Header(...)):
    claims = verify_token(authorization)

    game = active_games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if game["status"] != "active":
        raise HTTPException(status_code=400, detail="Game is not active")

    if claims["username"] != action.username:
        raise HTTPException(status_code=403, detail="Token does not match username")

    world = active_worlds.get(game_id)
    if not world:
        raise HTTPException(status_code=404, detail="World data not found")

    action_dict = action.dict()

    valid, reason = validate_action(action_dict, game, world)
    if not valid:
        print("VALIDATION FAILED:", reason)
        print("ACTION:", action_dict)
        print("PLAYER:", player if 'player' in locals() else "unknown")
        raise HTTPException(status_code=400, detail=reason)

    updated = apply_action(action_dict, game)
    active_games[game_id] = updated

    db = SessionLocal()
    try:
        session = db.query(GameSession).filter(GameSession.id == game_id).first()
        if session and session.state_path:
            with open(session.state_path, "w") as f:
                json.dump(updated, f)
            session.status = updated.get("status", "active")
            db.commit()
    finally:
        db.close()

    await ws_manager.broadcast(game_id, updated)

    return {"message": "action accepted", "state": updated}

@router.get("/{game_id}/state")
def get_game_state(game_id: str, authorization: str = Header(...)):
    claims = verify_token(authorization)

    game = active_games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # only player can see changes
    player_in_game = any(
        p["username"] == claims["username"]
        for p in game["players"]
    )
    if not player_in_game:
        raise HTTPException(status_code=403, detail="You are not in this game")

    return game

@router.websocket("/ws/{game_id}/{username}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, username: str):

    game = active_games.get(game_id)
    if not game:
        await websocket.close()
        return

    player_in_game = any(
        p["username"] == username
        for p in game["players"]
    )

    if not player_in_game:
        await websocket.close()
        return

    await ws_manager.connect(game_id, websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:

        ws_manager.disconnect(game_id, websocket)

        game = active_games.get(game_id)

        if game:

            # remove disconnected player
            game["players"] = [
                p for p in game["players"]
                if p["username"] != username
            ]

            print("Remaining players:", len(game["players"]))

            # remove active session if empty
            if len(game["players"]) == 0:

                print("Removing active session:", game_id)

                active_games.pop(game_id, None)
                active_worlds.pop(game_id, None)
