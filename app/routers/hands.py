from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db_session import get_db
from app.schemas import HandCreate, HandOut
from app.models.models import Hand, HandBid, Game
from app.services.lp_rules import parse_final_bid, compute_payout
from decimal import Decimal

router = APIRouter(prefix="/games/{game_id}/hands", tags=["hands"])

@router.post("", response_model=HandOut)
def create_hand(game_id: UUID, payload: HandCreate, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # roster validation
    roster_user_ids = {
        r.user_id for r in db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
    }
    if payload.winner_user_id not in roster_user_ids or payload.loser_user_id not in roster_user_ids:
        raise HTTPException(status_code=400, detail="Winner/loser must be players in this game")

    # parse final bid
    try:
        parsed = parse_final_bid(payload.final_bid_raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # compute payout
    bet = payload.bet_amount if payload.bet_amount is not None else Decimal(str(game.base_bet))
    amount = Decimal(str(compute_payout(float(bet), payload.is_nut, payload.is_skunk)))

    hand = Hand(
        game_id=game_id,
        hand_number=payload.hand_number,
        winner_user_id=payload.winner_user_id,
        loser_user_id=payload.loser_user_id,
        final_bid_raw=parsed.raw,
        final_bid_count=parsed.count,
        final_bid_digit=parsed.digit,
        is_nut=payload.is_nut,
        is_skunk=payload.is_skunk,
        amount_won=amount,
        notes=payload.notes,
    )
    db.add(hand)
    db.commit()
    db.refresh(hand)

    # optional bid trail
    if payload.bids:
        if not game.track_bid_trail:
            raise HTTPException(status_code=400, detail="This game does not track bid trail")
        for b in payload.bids:
            db.add(HandBid(
                hand_id=hand.id,
                user_id=b.user_id,
                bid_order=b.bid_order,
                bid_raw=b.bid_raw,
                bid_count=b.bid_count,
                bid_digit=b.bid_digit,
            ))
        db.commit()

    return hand