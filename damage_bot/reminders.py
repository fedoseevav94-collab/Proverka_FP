from __future__ import annotations

import asyncio
import logging
from datetime import timedelta, timezone

from aiogram import Bot
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import func, select

from damage_bot.config import Settings
from damage_bot.core.constants import ActionType, CaseStatus, FINAL_STATUSES
from damage_bot.core.managers import parse_manager_days_off
from damage_bot.db import CaseAction, DamageCase
from damage_bot.keyboards import reminder_keyboard
from damage_bot.messages import escalation_text, reminder_text, service_amount_request_text
from damage_bot.repository import create_case_action, due_reminder_cases, utcnow

logger = logging.getLogger(__name__)


async def reminder_loop(bot: Bot, session_factory: async_sessionmaker, settings: Settings) -> None:
    while True:
        try:
            await process_due_cases(bot, session_factory, settings)
        except Exception:
            logger.exception("Reminder loop failed")
        await asyncio.sleep(30)


async def process_due_cases(bot: Bot, session_factory: async_sessionmaker, settings: Settings) -> None:
    now = utcnow()
    async with session_factory() as session:
        due = await due_reminder_cases(session, now)
        for case_stub in due:
            case = await session.scalar(
                select(DamageCase)
                .where(DamageCase.id == case_stub.id)
                .options(
                    selectinload(DamageCase.car),
                    selectinload(DamageCase.fp_message),
                    selectinload(DamageCase.pv_return),
                )
            )
            if not case:
                continue
            if case.status == CaseStatus.WAITING_SERVICE_AMOUNT.value:
                await _send_service_amount_reminder(bot, session, case, settings)
                continue
            if case.reminders_sent >= settings.max_reminders:
                await _escalate(bot, settings, session, case)
                continue
            await _send_reminder(bot, session, case, settings)
        await _send_due_service_amount_reminders(bot, session, settings, now)
        await session.commit()


async def _send_service_amount_reminder(bot: Bot, session, case: DamageCase, settings: Settings) -> None:
    await bot.send_message(
        case.fp_message.chat_id,
        service_amount_request_text(case, settings.service_username),
        reply_to_message_id=case.fp_message.telegram_message_id,
        allow_sending_without_reply=False,
    )
    case.last_reminder_at = utcnow()
    case.first_check_due_at = case.last_reminder_at + timedelta(
        minutes=settings.service_amount_reminder_interval_minutes
    )
    await create_case_action(session, case.id, ActionType.SERVICE_AMOUNT_REQUESTED)


async def _send_due_service_amount_reminders(bot: Bot, session, settings: Settings, now) -> None:
    requested = (
        select(CaseAction.id)
        .where(
            CaseAction.case_id == DamageCase.id,
            CaseAction.action_type == ActionType.SERVICE_AMOUNT_REQUESTED.value,
        )
        .exists()
    )
    received = (
        select(CaseAction.id)
        .where(
            CaseAction.case_id == DamageCase.id,
            CaseAction.action_type == ActionType.SERVICE_AMOUNT_RECEIVED.value,
        )
        .exists()
    )
    cases = await session.scalars(
        select(DamageCase)
        .where(
            DamageCase.status.not_in([status.value for status in FINAL_STATUSES]),
            requested,
            ~received,
        )
        .options(selectinload(DamageCase.car), selectinload(DamageCase.fp_message))
    )
    for case in cases:
        latest_request_at = await session.scalar(
            select(func.max(CaseAction.created_at)).where(
                CaseAction.case_id == case.id,
                CaseAction.action_type == ActionType.SERVICE_AMOUNT_REQUESTED.value,
            )
        )
        if latest_request_at and latest_request_at.tzinfo is None:
            latest_request_at = latest_request_at.replace(tzinfo=timezone.utc)
        if latest_request_at and latest_request_at + timedelta(
            minutes=settings.service_amount_reminder_interval_minutes
        ) > now:
            continue
        await _send_service_amount_reminder(bot, session, case, settings)


async def _send_reminder(bot: Bot, session, case: DamageCase, settings: Settings) -> None:
    mention_override = None
    if not case.manager_name and not case.manager_username:
        mention_override = _manager_mentions_for_today(settings)
    await bot.send_message(
        case.fp_message.chat_id,
        reminder_text(case, mention_override),
        reply_markup=reminder_keyboard(case.id, case.category),
        reply_to_message_id=case.fp_message.telegram_message_id,
        allow_sending_without_reply=False,
    )
    case.reminders_sent += 1
    case.last_reminder_at = utcnow()
    case.status = getattr(CaseStatus, f"REMINDER_{case.reminders_sent}_SENT").value
    case.first_check_due_at = case.last_reminder_at + timedelta(minutes=settings.reminder_interval_minutes)
    await create_case_action(session, case.id, ActionType.REMINDER_SENT)


async def _escalate(bot: Bot, settings: Settings, session, case: DamageCase) -> None:
    text = escalation_text(case)
    target_chat_id = settings.admin_chat_id or case.fp_message.chat_id
    if settings.admin_chat_id:
        await bot.send_message(target_chat_id, text)
    else:
        await bot.send_message(
            target_chat_id,
            f"@{settings.supervisor_username}\n\n{text}",
            reply_to_message_id=case.fp_message.telegram_message_id,
            allow_sending_without_reply=False,
        )
    case.status = CaseStatus.ESCALATED_TO_SUPERVISOR.value
    case.escalated_at = utcnow()
    await create_case_action(session, case.id, ActionType.ESCALATED)


def _manager_mentions_for_today(settings: Settings) -> str | None:
    days_off = parse_manager_days_off(settings.manager_days_off)
    if not days_off:
        return None
    weekday = utcnow().weekday()
    mentions = [
        f"@{username}"
        for username, off_days in days_off.items()
        if weekday not in off_days
    ]
    return " ".join(mentions) if mentions else "Менеджеры"
