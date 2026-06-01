from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from damage_bot.core.constants import ActionType, CaseStatus, FINAL_STATUSES, MessageCategory
from damage_bot.core.matching import CarRef
from damage_bot.db import Car, CaseAction, DamageCase, FPMessage, PVReturn


async def car_refs(session: AsyncSession) -> list[CarRef]:
    rows = (await session.scalars(select(Car))).all()
    return [
        CarRef(
            id=car.id,
            brand=car.brand,
            model=car.model,
            original_plate=car.original_plate,
            normalized_plate=car.normalized_plate,
            digits_key=car.digits_key,
        )
        for car in rows
    ]


async def get_car(session: AsyncSession, car_id: int) -> Car | None:
    return await session.get(Car, car_id)


async def find_fp_message(session: AsyncSession, chat_id: int, message_id: int) -> FPMessage | None:
    return await session.scalar(
        select(FPMessage).where(FPMessage.chat_id == chat_id, FPMessage.telegram_message_id == message_id)
    )


async def find_pv_return(session: AsyncSession, chat_id: int, message_id: int) -> PVReturn | None:
    return await session.scalar(
        select(PVReturn).where(PVReturn.chat_id == chat_id, PVReturn.telegram_message_id == message_id)
    )


async def create_case_action(
    session: AsyncSession,
    case_id: int,
    action_type: ActionType,
    telegram_user_id: int | None = None,
    telegram_username: str | None = None,
    telegram_name: str | None = None,
    comment: str | None = None,
) -> None:
    session.add(
        CaseAction(
            case_id=case_id,
            action_type=action_type.value,
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            telegram_name=telegram_name,
            comment=comment,
        )
    )


async def create_damage_case_from_fp(
    session: AsyncSession,
    fp: FPMessage,
    manager_response_due_at: datetime | None = None,
) -> DamageCase | None:
    if fp.category not in {
        MessageCategory.DAMAGE_CHARGE_REQUIRED.value,
        MessageCategory.DAMAGE_NO_CHARGE_REQUIRED.value,
    }:
        return None
    if not fp.car_id:
        return None
    existing = await session.scalar(select(DamageCase).where(DamageCase.fp_message_id == fp.id))
    if existing:
        return existing
    case = DamageCase(
        car_id=fp.car_id,
        fp_message_id=fp.id,
        category=fp.category,
        status=CaseStatus.WAITING_FOR_RETURN.value,
        damage_description=fp.description or fp.text,
    )
    if fp.category == MessageCategory.DAMAGE_CHARGE_REQUIRED.value and manager_response_due_at is not None:
        case.status = CaseStatus.WAITING_MANAGER_ACTION.value
        case.first_check_due_at = manager_response_due_at
    session.add(case)
    await session.flush()
    await create_case_action(session, case.id, ActionType.CREATED_FROM_FP)
    return case


async def open_cases_for_return(session: AsyncSession, car_id: int, returned_at: datetime) -> list[DamageCase]:
    since = returned_at - timedelta(hours=72)
    query = (
        select(DamageCase)
        .join(FPMessage, FPMessage.id == DamageCase.fp_message_id)
        .options(selectinload(DamageCase.fp_message), selectinload(DamageCase.car))
        .where(
            DamageCase.car_id == car_id,
            DamageCase.status.not_in([status.value for status in FINAL_STATUSES]),
            FPMessage.created_at >= since,
            FPMessage.created_at <= returned_at,
        )
    )
    return list((await session.scalars(query)).all())


async def attach_return_to_cases(
    session: AsyncSession,
    pv_return: PVReturn,
    cases: list[DamageCase],
    first_delay_minutes: int,
) -> None:
    due = pv_return.created_at + timedelta(minutes=first_delay_minutes)
    for case in cases:
        case.pv_return_id = pv_return.id
        case.status = CaseStatus.WAITING_MANAGER_ACTION.value
        case.driver_name = pv_return.driver_name
        case.manager_name = pv_return.manager_name
        case.manager_username = pv_return.manager_username
        case.return_detected_at = pv_return.created_at
        case.first_check_due_at = due
        await create_case_action(session, case.id, ActionType.MATCHED_WITH_PV_RETURN)


async def due_reminder_cases(session: AsyncSession, now: datetime) -> list[DamageCase]:
    active_statuses = [
        CaseStatus.WAITING_MANAGER_ACTION.value,
        CaseStatus.MANAGER_SEEN.value,
        CaseStatus.WAITING_SERVICE_AMOUNT.value,
        CaseStatus.REMINDER_1_SENT.value,
        CaseStatus.REMINDER_2_SENT.value,
        CaseStatus.REMINDER_3_SENT.value,
    ]
    return list(
        (
            await session.scalars(
                select(DamageCase).where(
                    DamageCase.status.in_(active_statuses),
                    DamageCase.first_check_due_at.is_not(None),
                    DamageCase.first_check_due_at <= now,
                    DamageCase.escalated_at.is_(None),
                )
            )
        ).all()
    )


async def waiting_comment_case_for_user(session: AsyncSession, user_id: int) -> DamageCase | None:
    return await session.scalar(
        select(DamageCase).where(
            and_(
                DamageCase.status == CaseStatus.WAITING_CLOSE_COMMENT.value,
                DamageCase.closed_by_user_id == user_id,
            )
        )
    )


async def open_cases(session: AsyncSession) -> list[DamageCase]:
    return list(
        (
            await session.scalars(
                select(DamageCase)
                .where(DamageCase.status.not_in([status.value for status in FINAL_STATUSES]))
                .order_by(DamageCase.created_at.desc())
            )
        ).all()
    )


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

