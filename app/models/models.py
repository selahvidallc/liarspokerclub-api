import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import Boolean, Integer, Numeric, String, DateTime, ForeignKey, Text, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class Game(Base):
    __tablename__ = "games"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    scorekeeper_user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)

    nut_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    skunk_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    track_bid_trail: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    digit_order_mode: Mapped[str] = mapped_column(
        String(50),
        default="LP_STANDARD_2_LOW_0_SECOND_ACE_HIGH",
        nullable=False,
    )

    base_bet: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("5.00"), nullable=False)

    cards_per_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    bet_ladder: Mapped[list | None] = mapped_column(JSON, nullable=True)
    settlement_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="PER_HAND")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Hand(Base):
    __tablename__ = "hands"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("games.id"), nullable=False)

    hand_number: Mapped[int] = mapped_column(Integer, nullable=False)
    card_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    winner_user_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    loser_user_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    final_bid_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_bid_digit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_bid_raw: Mapped[str | None] = mapped_column(String(20), nullable=True)

    bet_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))

    is_nut: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_skunk: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    amount_won: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class GamePlayer(Base):
    __tablename__ = "game_players"
    __table_args__ = (
        UniqueConstraint("game_id", "user_id", name="uq_game_players_game_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("games.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class HandBid(Base):
    __tablename__ = "hand_bids"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hand_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("hands.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    bid_order: Mapped[int] = mapped_column(Integer, nullable=False)
    bid_count: Mapped[int] = mapped_column(Integer, nullable=False)
    bid_digit: Mapped[int] = mapped_column(Integer, nullable=False)
    bid_raw: Mapped[str] = mapped_column(String(20), nullable=False)

    is_nut: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_skunk: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class GamePreset(Base):
    __tablename__ = "game_presets"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)

    cards_per_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    base_bet: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("5.00"))
    bet_ladder: Mapped[list | None] = mapped_column(JSON, nullable=True)

    nut_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    skunk_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    track_bid_trail: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    digit_order_mode: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="LP_STANDARD_2_LOW_0_SECOND_ACE_HIGH",
    )

    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)