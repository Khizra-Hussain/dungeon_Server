from sqlalchemy import Column, String, ForeignKey
from db.database import Base

class Subscription(Base):
    __tablename__ = "subscriptions"

    player_id = Column(String, ForeignKey("players.id"), primary_key=True)
    editor_id = Column(String, ForeignKey("players.id"), primary_key=True)