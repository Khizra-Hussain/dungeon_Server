from sqlalchemy import Column, String, Integer, DateTime
from db.database import Base
import uuid
from datetime import datetime

class Player(Base):
    __tablename__ = "players"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True)
    password_hash = Column(String)
    role = Column(String)  # player | editor
    total_score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)