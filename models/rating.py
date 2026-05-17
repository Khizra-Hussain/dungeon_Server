from sqlalchemy import Column, String, Integer, ForeignKey
from db.database import Base

class WorldRating(Base):
    __tablename__ = "world_ratings"

    player_id = Column(String, ForeignKey("players.id"), primary_key=True)
    world_id = Column(String, ForeignKey("worlds.id"), primary_key=True)
    score = Column(Integer)