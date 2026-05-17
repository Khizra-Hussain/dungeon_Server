# Run with: uvicorn main:app --reload --port 5001

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import Base, engine
from routes.auth_routes import router as auth_router
from routes.world_routes import router as world_router
from routes.game_routes import router as game_router
from routes.editor_routes import router as editor_router
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

os.makedirs("data/worlds", exist_ok=True)
os.makedirs("data/gameStates", exist_ok=True)

app.include_router(auth_router)
app.include_router(world_router)
app.include_router(game_router)
app.include_router(editor_router)


@app.get("/")
def root():
    return {"status": "Module 1 server is running"}