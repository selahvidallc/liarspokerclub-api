from fastapi import FastAPI
from sqlalchemy import text
from app.db import engine
from fastapi.middleware.cors import CORSMiddleware

from app.routers.users import router as users_router
from app.routers.games import router as games_router
from app.routers.hands import router as hands_router
from app.routers.game_players import router as game_players_router
from app.routers.scoreboard import router as scoreboard_router
from app.routers.hands_resolve import router as hands_resolve_router
from app.routers.presets import router as presets_router

app = FastAPI(title="Liar's Poker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/db-test")
def db_test():
    with engine.connect() as conn:
        ts = conn.execute(text("SELECT now();")).scalar()
    return {"db_time": str(ts)}

app.include_router(users_router)
app.include_router(games_router)
app.include_router(hands_router)
app.include_router(game_players_router)
app.include_router(scoreboard_router)
app.include_router(hands_resolve_router)
app.include_router(presets_router)
