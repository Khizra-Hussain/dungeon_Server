from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import FileResponse
from db.database import SessionLocal
from sqlalchemy import func
from models.world import World
from models.player import Player
from datetime import datetime
from models.game import GameSession
from models.rating import WorldRating
from models.subscription import Subscription
from routes.auth_routes import verify_token
from models_pydantic import WorldUploadRequest, RatingRequest
import uuid
import json
import os

router = APIRouter(prefix="/worlds")

# upload world map
@router.post("/upload")
def upload_world(data: WorldUploadRequest,
                 authorization: str = Header(...)):
    claims = verify_token(authorization)
    if claims["role"] != "editor":
        raise HTTPException(status_code=403, detail="Only editors can upload worlds")

    creator_id = claims["player_id"]

    db = SessionLocal()
    try:
        existing_world = db.query(World).filter(
            World.creator_id == creator_id,
            World.name == data.name
        ).first()

        if existing_world:
            new_version = existing_world.version + 1
            world_id = existing_world.id
            file_path = f"data/worlds/{world_id}_v{new_version}.json"

            world_dict = data.dict()
            world_dict["world_id"] = world_id
            world_dict["version"] = new_version
            world_dict["created_by"] = creator_id
            world_dict["created_at"] = datetime.utcnow().isoformat()

            os.makedirs("data/worlds", exist_ok=True)
            with open(file_path, "w") as f:
                json.dump(world_dict, f)

            new_world = World(
                id=str(uuid.uuid4()),
                creator_id=creator_id,
                name=data.name,
                version=new_version,
                width=data.width,
                height=data.height,
                status="published",
                file_path=file_path,
                max_players=data.max_players,
                players_count=0,
                avg_rating=0
            )
            db.add(new_world)
            db.commit()
            return {"message": "world uploaded", "world_id": new_world.id, "version": new_version}
        else:
            new_version = 1
            world_id = str(uuid.uuid4())
            file_path = f"data/worlds/{world_id}.json"

            world_dict = data.dict()
            world_dict["world_id"] = world_id
            world_dict["version"] = new_version
            world_dict["created_by"] = creator_id
            world_dict["created_at"] = datetime.utcnow().isoformat()

            os.makedirs("data/worlds", exist_ok=True)
            with open(file_path, "w") as f:
                json.dump(world_dict, f)

            world = World(
                id=world_id,
                creator_id=creator_id,
                name=data.name,
                version=new_version,
                width=data.width,
                height=data.height,
                status="published",
                file_path=file_path,
                max_players=data.max_players,
                players_count=0,
                avg_rating=0
            )
            db.add(world)
            db.commit()
            return {"message": "world uploaded", "world_id": world_id, "version": new_version}
    finally:
        db.close()
# list of worlds
@router.get("/")
def list_worlds(authorization: str = Header(...)):
    claims = verify_token(authorization)
    player_id = claims["player_id"]

    db = SessionLocal()
    try:
        # check player subscribed or not
        subscriptions = db.query(Subscription).filter(
            Subscription.player_id == player_id
        ).all()

        # subscribed editor ids
        editor_ids = [s.editor_id for s in subscriptions]

        if not editor_ids:
            return {"worlds": []}

        subquery = db.query(
            World.name,
            World.creator_id,
            func.max(World.version).label("max_version")
        ).filter(
            World.creator_id.in_(editor_ids)
        ).group_by(
            World.name,
            World.creator_id
        ).subquery()

        worlds = db.query(World).join(
            subquery,
            (World.name == subquery.c.name)
            & (World.creator_id == subquery.c.creator_id)
            & (World.version == subquery.c.max_version)
        ).filter(
            World.status == "published"
        ).all()


        result = []
        for w in worlds:

            waiting_session = db.query(GameSession).filter(
                GameSession.world_id == w.id,
                GameSession.status == "waiting"
            ).first()

            result.append({
                "id": w.id,
                "name": w.name,
                "max_players": w.max_players,
                "can_join": waiting_session is not None,
                "game_id": waiting_session.id if waiting_session else None
            })

        return {"worlds": result}
    finally:
        db.close()

#editors's maps
@router.get("/{username}")
def editor_worlds(username: str, authorization: str = Header(...)):
    claims = verify_token(authorization)

    db = SessionLocal()
    try:
        editor = db.query(Player).filter(Player.username == username).first()
        if not editor:
            raise HTTPException(status_code=404, detail="Editor not found")

        worlds = db.query(World).filter(World.creator_id == editor.id).all()

        return {"worlds": [
            {
                "id": w.id,
                "name": w.name,
                "version": w.version,
                "status": w.status,
                "max_players": w.max_players,
                "width": w.width,
                "height": w.height,
                "created_at": w.created_at
            }
            for w in worlds
        ]}
    finally:
        db.close()
      
# download world
@router.get("/{world_id}/download")
def download_world(world_id: str):
    db = SessionLocal()
    try:
        world = db.query(World).filter(World.id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")
        if not os.path.exists(world.file_path):
            raise HTTPException(status_code=404, detail="World file not found on disk")
        with open(world.file_path) as f:
            return json.load(f)
    finally:
        db.close()


@router.delete("/{world_id}")
def delete_world(world_id: str, authorization: str = Header(...)):
    claims = verify_token(authorization)

    
    if claims["role"] != "editor":
        raise HTTPException(status_code=403, detail="Only editors can delete worlds")

    db = SessionLocal()
    try:
        world = db.query(World).filter(World.id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")

        if world.creator_id != claims["player_id"]:
            raise HTTPException(status_code=403, detail="You can only delete your own worlds")

        # active sessions check
        active = db.query(GameSession).filter(
            GameSession.world_id == world_id,
            GameSession.status.in_(["waiting", "active"])
        ).first()

        if active and active.id not in active_games:
            active.status = "finished"
            db.commit()
            active = None

        if active:
          raise HTTPException(status_code=400, detail="Cannot delete world with active sessions")

        db.delete(world)
        db.commit()
        return {"message": "world deleted"}
    finally:
        db.close()

@router.get("/{world_id}/stats")
def world_stats(world_id: str, authorization: str = Header(...)):
    claims = verify_token(authorization)

    db = SessionLocal()
    try:
        world = db.query(World).filter(World.id == world_id).first()
        if not world:
            raise HTTPException(status_code=404, detail="World not found")
        return {
            "world_id": world_id,
            "name": world.name,
            "players_count": world.players_count,
            "avg_rating": world.avg_rating
        }
    finally:
        db.close()


@router.post("/{world_id}/rate")
def rate_world(world_id: str, data: RatingRequest,
               authorization: str = Header(...)):
    claims = verify_token(authorization)

    if claims["role"] != "player":
        raise HTTPException(status_code=403, detail="Only players can rate worlds")

    if data.score < 1 or data.score > 5:
        raise HTTPException(status_code=400, detail="Score must be between 1 and 5")

    db = SessionLocal()
    try:
        # check if already rated
        existing = db.query(WorldRating).filter(
            WorldRating.player_id == claims["player_id"],
            WorldRating.world_id == world_id
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="Already rated")

        db.add(WorldRating(
            player_id=claims["player_id"],
            world_id=world_id,
            score=data.score
        ))
        db.commit()

        # avg_rating update
        all_ratings = db.query(WorldRating).filter(
            WorldRating.world_id == world_id
        ).all()

        world = db.query(World).filter(World.id == world_id).first()
        if world:
            world.avg_rating = sum(r.score for r in all_ratings) / len(all_ratings)
            db.commit()

        return {"message": "rating submitted", "score": data.score}
    finally:
        db.close()
