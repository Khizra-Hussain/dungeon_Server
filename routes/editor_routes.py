from fastapi import APIRouter, HTTPException, Header
from db.database import SessionLocal
from models.news import News
from models.subscription import Subscription
from models.player import Player
from routes.auth_routes import verify_token
from models_pydantic import NewsRequest
from datetime import datetime
import uuid

router = APIRouter(prefix="/editors")

# get all editors list
@router.get("/list")
def list_editors(authorization: str = Header(...)):
    claims = verify_token(authorization)
    db = SessionLocal()
    try:
        editors = db.query(Player).filter(
            Player.role == "editor"
        ).all()
        return {"editors": [
            {
                "id": e.id,
                "username": e.username
            }
            for e in editors
        ]}
    finally:
        db.close()

# publish news
@router.post("/{username}/news")
def publish_news(username: str, data: NewsRequest,
                 authorization: str = Header(...)):
    claims = verify_token(authorization)

    if claims["role"] != "editor":
        raise HTTPException(status_code=403, detail="Only editors can publish news")

    if claims["username"] != username:
        raise HTTPException(status_code=403, detail="You can only publish as yourself")

    db = SessionLocal()
    try:
        editor = db.query(Player).filter(Player.username == username).first()
        if not editor:
            raise HTTPException(status_code=404, detail="Editor not found")

        news = News(
            id=str(uuid.uuid4()),
            editor_id=editor.id,
            content=data.content,
            created_at=datetime.utcnow()
        )
        db.add(news)
        db.commit()
        return {"message": "news published"}
    finally:
        db.close()

# get news
@router.get("/{username}/news")
def get_news(username: str, authorization: str = Header(...)):
    claims = verify_token(authorization)

    db = SessionLocal()
    try:
        editor = db.query(Player).filter(Player.username == username).first()
        if not editor:
            raise HTTPException(status_code=404, detail="Editor not found")

        news_list = db.query(News).filter(
            News.editor_id == editor.id
        ).order_by(News.created_at.desc()).all()

        return {"editor_id": editor.id, "news": [
            {
                "id": n.id,
                "content": n.content,
                "created_at": n.created_at
            }
            for n in news_list
        ]}
    finally:
        db.close()

# subscribe
@router.post("/{username}/subscribe")
def subscribe(username: str, authorization: str = Header(...)):
    claims = verify_token(authorization)
    player_id = claims["player_id"]

    db = SessionLocal()
    try:
        editor = db.query(Player).filter(Player.username == username).first()
        if not editor:
            editor = db.query(Player).filter(Player.id == username).first()
        if not editor:
            raise HTTPException(status_code=404, detail="Editor not found")

        if player_id == editor.id:
            raise HTTPException(status_code=400, detail="Cannot subscribe to yourself")

        existing = db.query(Subscription).filter(
            Subscription.player_id == player_id,
            Subscription.editor_id == editor.id
        ).first()

        if existing:
            return {"message": "already subscribed", "editor": username}

        sub = Subscription(
            player_id=player_id,
            editor_id=editor.id
        )
        db.add(sub)
        db.commit()
        return {"message": "subscribed", "editor": username}
    finally:
        db.close()
