from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime
from datetime import datetime
from db.database import Base
import uuid

class World(Base):
    __tablename__ = "worlds"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    creator_id = Column(String, ForeignKey("players.id"))
    name = Column(String)
    version = Column(Integer, default=1)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String)  # draft | published | archived
    file_path = Column(String)
    max_players = Column(Integer)
    players_count = Column(Integer, default=0)
    avg_rating = Column(Float, default=0)
    total_time = Column(Integer, default=0)
