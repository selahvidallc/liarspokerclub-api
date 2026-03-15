from uuid import UUID
from datetime import datetime, UTC
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, or_

from app.db import get_db
from app.schemas import GameCreate, GameOut
from app.models.models import Game, GamePreset, GamePlayer, User


router = APIRouter(prefix="/games", tags=["games"])

@router.post("", response_model=GameOut)
def create_game(payload: GameCreate, db: Session = Depends(get_db)):
    preset = None
    if payload.preset_id:
        preset = db.query(GamePreset).filter(GamePreset.id == payload.preset_id).first()
        if not preset:
            raise HTTPException(status_code=404, detail="Preset not found")

    cards_per_hand = (
        payload.cards_per_hand
        if payload.cards_per_hand is not None
        else (preset.cards_per_hand if preset else 5)
    )

    if payload.bet_ladder is not None and len(payload.bet_ladder) > 0:
        bet_ladder = payload.bet_ladder
    elif preset and preset.bet_ladder:
        bet_ladder = preset.bet_ladder
    else:
        base = (
            payload.base_bet
            if payload.base_bet is not None
            else (str(preset.base_bet) if preset else "5.00")
        )
        bet_ladder = [float(base)] * cards_per_hand

    base_bet = Decimal(str(payload.base_bet)) if payload.base_bet is not None else Decimal(str(bet_ladder[0]))
 
    generated_title = f"Liar's Poker - {datetime.now().strftime('%Y-%m-%d %I:%M %p')}"

    final_title = (
        payload.title.strip()
        if payload.title and payload.title.strip() and payload.title.strip() != "Liar's Poker Game"
        else generated_title
    )
    game = Game(
        created_by_user_id=payload.created_by_user_id,
        scorekeeper_user_id=payload.scorekeeper_user_id,
        title=final_title,

        nut_enabled=payload.nut_enabled if not preset else preset.nut_enabled,
        skunk_enabled=payload.skunk_enabled if not preset else preset.skunk_enabled,
        track_bid_trail=payload.track_bid_trail if not preset else preset.track_bid_trail,
        digit_order_mode=payload.digit_order_mode if not preset else preset.digit_order_mode,

        cards_per_hand=cards_per_hand,
        base_bet=base_bet,
        bet_ladder=bet_ladder,
        settlement_mode=payload.settlement_mode,
    )

    db.add(game)
    db.flush()

    auto_player_ids = {
        payload.created_by_user_id,
        payload.scorekeeper_user_id,
    }

    for user_id in auto_player_ids:
        db.add(GamePlayer(game_id=game.id, user_id=user_id))

    db.commit()
    db.refresh(game)
    return game

@router.get("", response_model=list[GameOut])
def list_games(db: Session = Depends(get_db)):
    return db.query(Game).order_by(Game.created_at.desc()).all()

@router.get("/my", response_model=list[GameOut])
def list_my_games(user_id: UUID, db: Session = Depends(get_db)):
    player_game_ids_subquery = (
        db.query(GamePlayer.game_id)
        .filter(GamePlayer.user_id == user_id)
    )

    games = (
        db.query(Game)
        .filter(
            or_(
                Game.created_by_user_id == user_id,
                Game.scorekeeper_user_id == user_id,
                Game.id.in_(player_game_ids_subquery),
            )
        )
        .order_by(Game.created_at.desc())
        .all()
    )

    return games

@router.get("/{game_id}", response_model=GameOut)
def get_game(game_id: UUID, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game

@router.get("/{game_id}/players")
def list_game_players(game_id: UUID, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    rows = (
        db.query(User.id, User.display_name)
        .join(GamePlayer, GamePlayer.user_id == User.id)
        .filter(GamePlayer.game_id == game_id)
        .order_by(User.display_name)
        .all()
    )

    return {
        "game_id": str(game_id),
        "players": [
            {
                "id": str(row.id),
                "display_name": row.display_name,
            }
            for row in rows
        ],
    }

@router.get("/{game_id}/settings")
def get_game_settings(game_id: UUID, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return {
        "id": str(game.id),
        "title": game.title,
        "cards_per_hand": game.cards_per_hand,
        "base_bet": str(game.base_bet),
        "bet_ladder": game.bet_ladder,
        "settlement_mode": game.settlement_mode,
        "nut_enabled": game.nut_enabled,
        "skunk_enabled": game.skunk_enabled,
        "track_bid_trail": game.track_bid_trail,
        "digit_order_mode": game.digit_order_mode,
    }
@router.get("/{game_id}/hand-progress")
def get_hand_progress(game_id: UUID, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    rows = db.execute(
        text("""
            SELECT hand_number, COUNT(DISTINCT card_number) AS card_count
            FROM hands
            WHERE game_id = :gid
            GROUP BY hand_number
            ORDER BY hand_number
        """),
        {"gid": str(game_id)},
    ).mappings().all()

    if not rows:
        current_hand_number = 1
        cards_played_in_current_hand = 0
    else:
        last = rows[-1]
        last_hand_number = int(last["hand_number"])
        last_count = int(last["card_count"])

        if last_count >= int(game.cards_per_hand):
            current_hand_number = last_hand_number + 1
            cards_played_in_current_hand = 0
        else:
            current_hand_number = last_hand_number
            cards_played_in_current_hand = last_count

    return {
        "game_id": str(game_id),
        "cards_per_hand": int(game.cards_per_hand),
        "current_hand_number": current_hand_number,
        "cards_played_in_current_hand": cards_played_in_current_hand,
        "cards_remaining_in_current_hand": max(0, int(game.cards_per_hand) - cards_played_in_current_hand),
        "hand_complete": cards_played_in_current_hand >= int(game.cards_per_hand) and int(game.cards_per_hand) > 0,
    }
@router.post("/{game_id}/players")
def add_player_to_game(game_id: UUID, user_id: UUID, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = (
        db.query(GamePlayer)
        .filter(GamePlayer.game_id == game_id, GamePlayer.user_id == user_id)
        .first()
    )
    if existing:
        return {"ok": True, "message": "Player already in game"}

    gp = GamePlayer(game_id=game_id, user_id=user_id)
    db.add(gp)
    db.commit()

    return {"ok": True, "message": "Player added"}


@router.delete("/{game_id}/players/{user_id}")
def remove_player_from_game(game_id: UUID, user_id: UUID, db: Session = Depends(get_db)):
    row = (
        db.query(GamePlayer)
        .filter(GamePlayer.game_id == game_id, GamePlayer.user_id == user_id)
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="Player not found in game")

    db.delete(row)
    db.commit()

    return {"ok": True, "message": "Player removed"}

@router.post("/{game_id}/finalize")
def finalize_game(game_id: UUID, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if getattr(game, "status", "OPEN") == "FINALIZED":
        return {
            "ok": True,
            "message": "Game already finalized",
            "status": game.status,
            "finalized_at": game.finalized_at,
        }

    game.status = "FINALIZED"
    game.finalized_at = datetime.now(UTC)
    db.commit()
    db.refresh(game)

    return {
        "ok": True,
        "message": "Game finalized",
        "status": game.status,
        "finalized_at": game.finalized_at,
    }