# all the json shapes
from pydantic import BaseModel
from typing import Optional, List

class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str  # "player" or "editor"

class LoginRequest(BaseModel):
    username: str
    password: str
    role: str

class ActionRequest(BaseModel):
    game_id: str
    username: str
    action_type: str
    payload: dict
    timestamp: str

class RatingRequest(BaseModel):
    score: int  # 1 to 5

class NewsRequest(BaseModel):
    content: str

class WorldUploadRequest(BaseModel):
    name: str
    width: int
    height: int
    max_players: int
    tiles: List[dict]     
    entities: List[dict]
