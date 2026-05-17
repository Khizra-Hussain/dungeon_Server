from fastapi import APIRouter, HTTPException
from db.database import SessionLocal
from models.player import Player
from jose import jwt
from passlib.context import CryptContext
import uuid
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth")

SECRET = "mysecretkey"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_token(authorization: str) -> dict:
    try:
        token = authorization.replace("Bearer ", "")
        return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def hash_password(password: str):
    password = password[:72]
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str):
    return pwd_context.verify(password, hashed)



# REGISTER
@router.post("/register")
def register(data: dict):
    db = SessionLocal()

    try:
        username = data.get("username")
        password = data.get("password")
        role = data.get("role", "player")

        if not username or not password:
            return {"error": "missing fields"}
        
        if role not in ["player", "editor"]:
            return {"error": "invalid role"}

        existing = db.query(Player).filter(Player.username == username).first()
        if existing:
            return {"error": "username already exists"}

        player_id = str(uuid.uuid4())

        player = Player(
            id=player_id,
            username=username,
            password_hash=hash_password(password),
            role=role,
            created_at=datetime.utcnow()
        )

        db.add(player)
        db.commit()

        
        token = jwt.encode(
            {
                "player_id": player_id,
                "role": role,
                "exp": datetime.utcnow() + timedelta(hours=24)
            },
            SECRET,
            algorithm=ALGORITHM
        )

        return {
            "message": "user created",
            "token": token,
            "player_id": player_id,
            "role": role
            
        }

    finally:
        db.close()


# LOGIN
@router.post("/login")
def login(data: dict):
    db = SessionLocal()

    try:
        username = data.get("username")
        password = data.get("password")
        role = data.get("role")

        if not username or not password or not role:
            return {"error": "missing fields"}

        player = db.query(Player).filter(Player.username == username).first()

        if not player:
            return {"error": "invalid credentials"}
        if player.role != role:
            return {"error": "invalid role"}

        if not verify_password(password, player.password_hash):
            return {"error": "invalid credentials"}

        token = jwt.encode(
            {
                "player_id": player.id,
                "role": player.role,
                "exp": datetime.utcnow() + timedelta(hours=24)
            },
            SECRET,
            algorithm=ALGORITHM
        )

        return {
            "token": token,
            "player_id": player.id,
            "role": player.role,

        }

    finally:
        db.close()
