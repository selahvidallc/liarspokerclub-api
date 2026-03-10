from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.models import GamePreset

router = APIRouter(prefix="/presets", tags=["presets"])

@router.get("/games")
def list_game_presets(favorites_only: bool = True, db: Session = Depends(get_db)):
    q = db.query(GamePreset).order_by(GamePreset.is_favorite.desc(), GamePreset.name.asc())
    if favorites_only:
        q = q.filter(GamePreset.is_favorite == True)  # noqa: E712
    rows = q.all()
    return {
        "presets": [
            {
                "id": str(p.id),
                "name": p.name,
                "cards_per_hand": p.cards_per_hand,
                "base_bet": str(p.base_bet),
                "nut_enabled": p.nut_enabled,
                "skunk_enabled": p.skunk_enabled,
                "track_bid_trail": p.track_bid_trail,
                "digit_order_mode": p.digit_order_mode,
                "is_favorite": p.is_favorite,
            }
            for p in rows
        ]
    }