from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db_session import get_db
from app.schemas import HandCreate, HandOut, HandUpdate, HandCardGroupUpdate
from app.models.models import Hand, HandBid, Game, GamePlayer
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

@router.patch("/{hand_id}", response_model=HandOut)
def update_hand(
    game_id: UUID,
    hand_id: UUID,
    payload: HandUpdate,
    db: Session = Depends(get_db),
):
    hand = (
        db.query(Hand)
        .filter(Hand.id == hand_id, Hand.game_id == game_id)
        .first()
    )

    if not hand:
        raise HTTPException(status_code=404, detail="Hand not found")

    if payload.winner_user_id is not None:
        hand.winner_user_id = payload.winner_user_id

    if payload.loser_user_id is not None:
        hand.loser_user_id = payload.loser_user_id

    if payload.amount_won is not None:
        hand.amount_won = payload.amount_won

    if payload.final_bid_raw is not None:
        hand.final_bid_raw = payload.final_bid_raw.strip() or None

    if payload.notes is not None:
        hand.notes = payload.notes.strip() or None

    db.add(hand)
    db.commit()
    db.refresh(hand)
    return hand

@router.patch("/by-card", response_model=dict)
def update_card_group(
    game_id: UUID,
    payload: HandCardGroupUpdate,
    db: Session = Depends(get_db),
):
    existing_rows = (
        db.query(Hand)
        .filter(
            Hand.game_id == game_id,
            Hand.hand_number == payload.hand_number,
            Hand.card_number == payload.card_number,
        )
        .order_by(Hand.created_at.asc(), Hand.id.asc())
        .all()
    )

    if not existing_rows:
        raise HTTPException(status_code=404, detail="Card group not found")

    participant_ids = set()
    for row in existing_rows:
        if row.winner_user_id:
            participant_ids.add(row.winner_user_id)
        if row.loser_user_id:
            participant_ids.add(row.loser_user_id)

    if payload.winner_user_id not in participant_ids:
        raise HTTPException(
            status_code=400,
            detail="Selected winner must already be a participant in this card",
        )

    loser_ids = [pid for pid in participant_ids if pid != payload.winner_user_id]
    if not loser_ids:
        raise HTTPException(
            status_code=400,
            detail="A card must have at least one loser",
        )

    template = existing_rows[0]

    for row in existing_rows:
        db.delete(row)
    db.flush()

    created_ids = []
    for loser_id in loser_ids:
        new_row = Hand(
            game_id=game_id,
            hand_number=payload.hand_number,
            card_number=payload.card_number,
            winner_user_id=payload.winner_user_id,
            loser_user_id=loser_id,
            final_bid_raw=(payload.final_bid_raw.strip() if payload.final_bid_raw else None),
            final_bid_count=template.final_bid_count,
            final_bid_digit=template.final_bid_digit,
            is_nut=template.is_nut,
            is_skunk=template.is_skunk,
            amount_won=payload.amount_won,
            notes=(payload.notes.strip() if payload.notes else None),
        )
        db.add(new_row)
        db.flush()
        created_ids.append(str(new_row.id))

    db.commit()

    return {
        "ok": True,
        "game_id": str(game_id),
        "hand_number": payload.hand_number,
        "card_number": payload.card_number,
        "winner_user_id": str(payload.winner_user_id),
        "loser_count": len(loser_ids),
        "created_row_ids": created_ids,
    }