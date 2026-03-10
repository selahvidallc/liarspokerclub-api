from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db_session import get_db
from app.models.models import Game, User, GamePlayer
from app.schemas import GamePlayerAdd, GamePlayerOut

router = APIRouter(prefix="/games/{game_id}/players", tags=["game_players"])

@router.post("", response_model=GamePlayerOut)
def add_player(game_id: UUID, payload: GamePlayerAdd, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    exists = db.query(GamePlayer).filter(
        GamePlayer.game_id == game_id,
        GamePlayer.user_id == payload.user_id
    ).first()
    if exists:
        return exists

    gp = GamePlayer(game_id=game_id, user_id=payload.user_id)
    db.add(gp)
    db.commit()
    db.refresh(gp)
    return gp

@router.get("", response_model=list[GamePlayerOut])
def list_players(game_id: UUID, db: Session = Depends(get_db)):
    return db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()