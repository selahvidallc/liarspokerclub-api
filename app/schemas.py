from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime

# ---------- Users ----------
class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    grant_login_access: bool = True

class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str

    class Config:
        from_attributes = True

# ---------- Games ----------
class GameCreate(BaseModel):
    created_by_user_id: UUID
    scorekeeper_user_id: UUID
    title: str = ""

    preset_id: Optional[UUID] = None

    cards_per_hand: Optional[int] = Field(default=None, ge=1, le=50)
    base_bet: Optional[str] = None
    bet_ladder: Optional[list[float]] = None

    nut_enabled: bool = True
    skunk_enabled: bool = True
    track_bid_trail: bool = False
    digit_order_mode: str = "LP_STANDARD_2_LOW_0_SECOND_ACE_HIGH"

    settlement_mode: str = "PER_HAND"

class GameOut(BaseModel):
    id: UUID
    created_by_user_id: UUID
    scorekeeper_user_id: UUID
    title: str

    nut_enabled: bool
    skunk_enabled: bool
    track_bid_trail: bool
    digit_order_mode: str

    base_bet: str | float
    cards_per_hand: int
    bet_ladder: list[float] | None
    settlement_mode: str

    status: str
    finalized_at: Optional[datetime] = None

    class Config:
        from_attributes = True
# ---------- Hands ----------
class HandBidIn(BaseModel):
    user_id: UUID
    bid_order: int
    bid_raw: str
    bid_count: int
    bid_digit: int

class HandCreate(BaseModel):
    hand_number: int
    winner_user_id: UUID
    loser_user_id: UUID
    game_id: UUID
    final_bid_raw: str  # e.g. "8A" or "110"
    bet_amount: Decimal = Field(default=Decimal("0.00"))
    # scorekeeper marks these; backend computes payout
    is_nut: bool = False
    is_skunk: bool = False

    # optional override per hand; else uses game.base_bet
    bet_amount: Optional[Decimal] = None

    notes: Optional[str] = None

    # Optional: only send if game.track_bid_trail=true
    bids: Optional[List[HandBidIn]] = None

class HandOut(BaseModel):
    id: UUID
    game_id: UUID
    hand_number: int
    card_number: int
    winner_user_id: Optional[UUID]
    loser_user_id: Optional[UUID]
    final_bid_raw: Optional[str]
    final_bid_count: Optional[int]
    final_bid_digit: Optional[int]
    is_nut: bool
    is_skunk: bool
    amount_won: Optional[Decimal]
    notes: Optional[str]
    bet_amount: Decimal = Field(default=Decimal("0.00"))
    class Config:
        from_attributes = True

class GamePlayerAdd(BaseModel):
    user_id: UUID

class GamePlayerOut(BaseModel):
    id: UUID
    game_id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True   
         
class HandResolveCreate(BaseModel):
    # optional: if omitted, backend auto-assigns next hand number
    hand_number: Optional[int] = Field(default=None, ge=1)

    bid_owner_user_id: UUID
    bid_owner_won: bool

    # Your existing format: "3x7" where 10 is "0" and Ace is "1"
    final_bid_raw: str = Field(min_length=3, max_length=20)

    # Optional override; if null uses game.base_bet
    bet_amount: Optional[str] = None  # keep as string to avoid Decimal JSON quirks

    is_nut: bool = False
    is_skunk: bool = False

    notes: Optional[str] = None


class HandResolveOut(BaseModel):
    game_id: UUID
    hand_number: int
    card_number: int
    created_hand_ids: list[UUID]
    rows_created: int

class UserSyncIn(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)

class UserSyncOut(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str
    created: bool

    class Config:
        from_attributes = True