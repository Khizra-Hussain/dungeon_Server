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

#publish news
@router.post("/{editor_id}/news")
def publish_news(editor_id: str, data: NewsRequest,
                 authorization: str = Header(...)):
    claims = verify_token(authorization)
    #only editor can
    if claims["role"] != "editor":
        raise HTTPException(status_code=403, detail="Only editors can publish news")
    #only editor's id
    if claims["player_id"] != editor_id:
        raise HTTPException(status_code=403, detail="You can only publish as yourself")

    db = SessionLocal()
    try:
        news = News(
            id=str(uuid.uuid4()),
            editor_id=editor_id,
            content=data.content,
            created_at=datetime.utcnow()
        )
        db.add(news)
        db.commit()
        return {"message": "news published"}
    finally:
        db.close()


@router.get("/{editor_id}/news")
def get_news(editor_id: str, authorization: str = Header(...)):
    claims = verify_token(authorization)

    db = SessionLocal()
    try:
        news_list = db.query(News).filter(
            News.editor_id == editor_id
        ).order_by(News.created_at.desc()).all()

        return {"editor_id": editor_id, "news": [
            {
                "id": n.id,
                "content": n.content,
                "created_at": n.created_at
            }
            for n in news_list
        ]}
    finally:
        db.close()


@router.post("/{editor_id}/subscribe")
def subscribe(editor_id: str, authorization: str = Header(...)):
    claims = verify_token(authorization)
    player_id = claims["player_id"]

    
    if player_id == editor_id:
        raise HTTPException(status_code=400, detail="Cannot subscribe to yourself")

    db = SessionLocal()
    try:
        existing = db.query(Subscription).filter(
            Subscription.player_id == player_id,
            Subscription.editor_id == editor_id
        ).first()

        if existing:
            return {"message": "already subscribed", "editor_id": editor_id}

        sub = Subscription(
            player_id=player_id,
            editor_id=editor_id
        )
        db.add(sub)
        db.commit()
        return {"message": "subscribed", "editor_id": editor_id}
    finally:
        db.close()