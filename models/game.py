from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from db.database import Base
import uuid
from datetime import datetime

class GameSession(Base):
    __tablename__ = "game_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    world_id = Column(String, ForeignKey("worlds.id"))
    world_version = Column(Integer)
    status = Column(String)  # waiting , active,  finished
    current_turn = Column(Integer, default=0)
    winner_id = Column(String, ForeignKey("players.id"), nullable=True)
    state_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)