from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Car(Base, TimestampMixin):
    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand: Mapped[str | None] = mapped_column(String(128))
    model: Mapped[str | None] = mapped_column(String(128))
    original_plate: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_plate: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    digits_key: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    owner: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str | None] = mapped_column(String(128))
    raw_excel_row_json: Mapped[str | None] = mapped_column(Text)


class FPMessage(Base):
    __tablename__ = "fp_messages"
    __table_args__ = (UniqueConstraint("telegram_message_id", "chat_id", name="uq_fp_message_chat"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    chat_id: Mapped[int] = mapped_column(Integer, nullable=False)
    sender_id: Mapped[int | None] = mapped_column(Integer)
    sender_username: Mapped[str | None] = mapped_column(String(128))
    sender_name: Mapped[str | None] = mapped_column(String(256))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    plate_raw: Mapped[str | None] = mapped_column(String(32))
    plate_normalized: Mapped[str | None] = mapped_column(String(32))
    car_id: Mapped[int | None] = mapped_column(ForeignKey("cars.id"))
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    has_media: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    car: Mapped[Car | None] = relationship()


class PVReturn(Base):
    __tablename__ = "pv_returns"
    __table_args__ = (UniqueConstraint("telegram_message_id", "chat_id", name="uq_pv_return_chat"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    chat_id: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    operation_type: Mapped[str | None] = mapped_column(String(64))
    plate_raw: Mapped[str | None] = mapped_column(String(32))
    plate_normalized: Mapped[str | None] = mapped_column(String(32))
    car_id: Mapped[int | None] = mapped_column(ForeignKey("cars.id"))
    driver_name: Mapped[str | None] = mapped_column(String(256))
    manager_name: Mapped[str | None] = mapped_column(String(256))
    manager_username: Mapped[str | None] = mapped_column(String(128))
    balance: Mapped[str | None] = mapped_column(String(64))
    deposit: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    car: Mapped[Car | None] = relationship()


class DamageCase(Base, TimestampMixin):
    __tablename__ = "damage_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    car_id: Mapped[int] = mapped_column(ForeignKey("cars.id"), nullable=False)
    fp_message_id: Mapped[int] = mapped_column(ForeignKey("fp_messages.id"), nullable=False, unique=True)
    pv_return_id: Mapped[int | None] = mapped_column(ForeignKey("pv_returns.id"))
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    driver_name: Mapped[str | None] = mapped_column(String(256))
    manager_name: Mapped[str | None] = mapped_column(String(256))
    manager_username: Mapped[str | None] = mapped_column(String(128))
    damage_description: Mapped[str] = mapped_column(Text, nullable=False)
    return_detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_check_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reminders_sent: Mapped[int] = mapped_column(Integer, default=0)
    last_reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by_user_id: Mapped[int | None] = mapped_column(Integer)
    close_comment: Mapped[str | None] = mapped_column(Text)
    close_type: Mapped[str | None] = mapped_column(String(64))
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    car: Mapped[Car] = relationship()
    fp_message: Mapped[FPMessage] = relationship()
    pv_return: Mapped[PVReturn | None] = relationship()


class CaseAction(Base):
    __tablename__ = "case_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("damage_cases.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    telegram_user_id: Mapped[int | None] = mapped_column(Integer)
    telegram_username: Mapped[str | None] = mapped_column(String(128))
    telegram_name: Mapped[str | None] = mapped_column(String(256))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def make_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
