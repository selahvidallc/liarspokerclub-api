from __future__ import annotations

from uuid import UUID, uuid4
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.models import Game, Hand, GamePlayer
from app.schemas import HandResolveCreate, HandResolveOut

router = APIRouter(prefix="/games", tags=["hands"])


def parse_final_bid(raw: str):
    """
    Accepts:
      3x7
      4x0  (10 stored as 0)
      5x1  (Ace stored as 1)
    """
    if not raw:
        raise ValueError("final_bid_raw is required")

    value = raw.strip().lower().replace(" ", "")
    if "x" not in value:
        raise ValueError("final_bid_raw must look like '3x7'")

    left, right = value.split("x", 1)

    try:
        count = int(left)
    except ValueError:
        raise ValueError("Bid count must be an integer")

    try:
        digit = int(right)
    except ValueError:
        raise ValueError("Bid digit must be an integer")

    if count < 1:
        raise ValueError("Bid count must be at least 1")

    if digit not in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]:
        raise ValueError("Bid digit must be 0-9 where 0=10 and 1=Ace")

    return SimpleNamespace(raw=raw, count=count, digit=digit)


def compute_payout(bet: float, is_nut: bool, is_skunk: bool) -> float:
    # Nut trumps skunk, only one double
    if is_nut:
        return float(bet) * 2
    if is_skunk:
        return float(bet) * 2
    return float(bet)


@router.post("/{game_id}/hands/resolve", response_model=HandResolveOut)
def resolve_hand(
    game_id: UUID,
    payload: HandResolveCreate,
    db: Session = Depends(get_db),
    x_user_id: UUID = Header(..., alias="X-User-Id"),
):
    game: Game | None = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if getattr(game, "status", "OPEN") == "FINALIZED":
        raise HTTPException(
            status_code=400,
            detail="Game has been finalized. Scoring is locked."
        )

    if game.scorekeeper_user_id != x_user_id:
        raise HTTPException(
            status_code=403,
            detail="Only the scorekeeper can change this game",
        )
    roster = (
        db.query(GamePlayer)
        .filter(
            GamePlayer.game_id == game_id,
            GamePlayer.is_active == True,
        )
        .all()
    )
    roster_user_ids = [r.user_id for r in roster]

    if payload.bid_owner_user_id not in roster_user_ids:
        raise HTTPException(status_code=400, detail="Bid owner must be a player in this game")

    if len(roster_user_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 players to score a hand")

    try:
        parsed = parse_final_bid(payload.final_bid_raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # determine next card number within this hand
    if payload.hand_number is not None:
        hand_number = int(payload.hand_number)
    else:
        max_n = db.execute(
            text("SELECT COALESCE(MAX(hand_number), 0) FROM hands WHERE game_id = :gid"),
            {"gid": str(game_id)},
        ).scalar()
        hand_number = int(max_n) + 1

    # determine next card number within this hand
    max_card_n = db.execute(
        text("""
            SELECT COALESCE(MAX(card_number), 0)
            FROM hands
            WHERE game_id = :gid
              AND hand_number = :hand_number
        """),
        {
            "gid": str(game_id),
            "hand_number": hand_number,
        },
    ).scalar()
    card_number = int(max_card_n) + 1
    if card_number > int(game.cards_per_hand):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Hand {hand_number} is already complete. "
                "Start a new hand before scoring again."
            ),
        )
    # nut overrides skunk
    is_nut = bool(payload.is_nut)
    is_skunk = bool(payload.is_skunk) if not is_nut else False

    # determine bet amount:
    # 1) explicit override from payload
    # 2) game.bet_ladder[card_number-1]
    # 3) fallback to game.base_bet
    if payload.bet_amount is not None:
        try:
            bet = Decimal(str(payload.bet_amount))
        except (InvalidOperation, ValueError):
            raise HTTPException(status_code=400, detail="Invalid bet_amount")
    else:
        ladder = game.bet_ladder if getattr(game, "bet_ladder", None) else None

        if ladder and isinstance(ladder, list) and len(ladder) > 0:
            idx = card_number - 1
            if idx < 0:
                idx = 0
            if idx >= len(ladder):
                idx = len(ladder) - 1
            bet = Decimal(str(ladder[idx]))
        else:
            bet = Decimal(str(game.base_bet))

    amount = Decimal(str(compute_payout(float(bet), is_nut, is_skunk)))

    bid_owner = payload.bid_owner_user_id
    created_ids: list[UUID] = []

    pairs: list[tuple[UUID, UUID]] = []
    if payload.bid_owner_won:
        for other in roster_user_ids:
            if other == bid_owner:
                continue
            pairs.append((bid_owner, other))
    else:
        for other in roster_user_ids:
            if other == bid_owner:
                continue
            pairs.append((other, bid_owner))

    for winner_id, loser_id in pairs:
        h = Hand(
            id=uuid4(),
            game_id=game_id,
            hand_number=hand_number,
            card_number=card_number,
            winner_user_id=winner_id,
            loser_user_id=loser_id,
            final_bid_raw=parsed.raw,
            final_bid_count=parsed.count,
            final_bid_digit=parsed.digit,
            bet_amount=bet,
            is_nut=is_nut,
            is_skunk=is_skunk,
            amount_won=amount,
            notes=payload.notes,
        )
        db.add(h)
        created_ids.append(h.id)

    db.commit()

    return HandResolveOut(
        game_id=game_id,
        hand_number=hand_number,
        card_number=card_number,
        created_hand_ids=created_ids,
        rows_created=len(created_ids),
    )