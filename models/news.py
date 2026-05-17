from sqlalchemy import Column, String, DateTime, ForeignKey
from db.database import Base
import uuid
from datetime import datetime

class News(Base):
    __tablename__ = "news"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    editor_id = Column(String, ForeignKey("players.id"))
    content = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)