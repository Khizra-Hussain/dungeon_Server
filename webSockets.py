from fastapi import WebSocket

active_connections: dict[str, list[WebSocket]] = {}


async def connect(game_id: str, websocket: WebSocket):
    #add player in list
    await websocket.accept()
    if game_id not in active_connections:
        active_connections[game_id] = []
    active_connections[game_id].append(websocket)


def disconnect(game_id: str, websocket: WebSocket):
   #remove player 
    if game_id in active_connections:
        active_connections[game_id].remove(websocket)
        if len(active_connections[game_id]) == 0:
            del active_connections[game_id]


async def broadcast(game_id: str, state: dict):
    connections = active_connections.get(game_id, [])

    for websocket in connections.copy():
        try:
            await websocket.send_json(state)
        except Exception:
            connections.remove(websocket)