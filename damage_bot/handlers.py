from __future__ import annotations

import logging
from datetime import timezone

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ForceReply, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from damage_bot.config import Settings
from damage_bot.core.classifier import classify_close_comment
from damage_bot.core.constants import ActionType, CaseStatus, MessageCategory
from damage_bot.core.matching import MatchStatus, match_car
from damage_bot.core.parsers import parse_fp_message, parse_pv_return
from damage_bot.core.plates import equivalent_chat_ids
from damage_bot.db import DamageCase, FPMessage, PVReturn
from damage_bot.fleet import reload_cars_from_excel
from damage_bot.keyboards import reminder_keyboard
from damage_bot.messages import close_comment_prompt, diagnostic_text
from damage_bot.repository import (
    attach_return_to_cases,
    car_refs,
    create_case_action,
    create_damage_case_from_fp,
    find_fp_message,
    find_pv_return,
    get_car,
    open_cases,
    open_cases_for_return,
    waiting_comment_case_for_user,
    utcnow,
)

logger = logging.getLogger(__name__)


def register_handlers(dp: Dispatcher, session_factory: async_sessionmaker, settings: Settings) -> None:
    async def start_wrapper(message: Message) -> None:
        await handle_start(message, settings)

    async def help_wrapper(message: Message) -> None:
        await handle_help(message, settings)

    async def reload_wrapper(message: Message) -> None:
        await handle_reload_cars(message, session_factory, settings)

    async def status_wrapper(message: Message) -> None:
        await handle_status(message, session_factory, settings)

    async def open_cases_wrapper(message: Message) -> None:
        await handle_open_cases(message, session_factory, settings)

    async def close_case_wrapper(message: Message) -> None:
        await handle_close_case(message, session_factory, settings)

    async def cancel_case_wrapper(message: Message) -> None:
        await handle_cancel_case(message, session_factory, settings)

    async def callback_wrapper(callback: CallbackQuery, bot: Bot) -> None:
        await handle_callback(callback, bot, session_factory)

    async def message_wrapper(message: Message, bot: Bot) -> None:
        await handle_message(message, bot, session_factory, settings)

    dp.message.register(start_wrapper, Command("start"))
    dp.message.register(help_wrapper, Command("help"))
    dp.message.register(reload_wrapper, Command("reload_cars"))
    dp.message.register(status_wrapper, Command("status"))
    dp.message.register(open_cases_wrapper, Command("open_cases"))
    dp.message.register(close_case_wrapper, Command("close_case"))
    dp.message.register(cancel_case_wrapper, Command("cancel_case"))
    dp.callback_query.register(callback_wrapper, F.data.regexp(r"^(seen|request_close|close_no_charge):\d+$"))
    dp.message.register(message_wrapper)


async def handle_start(message: Message, settings: Settings) -> None:
    if not _has_bot_access(message, settings):
        await _answer_no_access(message)
        return
    await message.answer("Бот контроля закрытия повреждений запущен. Используйте /help.")


async def handle_help(message: Message, settings: Settings) -> None:
    if not _has_bot_access(message, settings):
        await _answer_no_access(message)
        return
    await message.answer(
        "/reload_cars — загрузить авто из Excel\n"
        "/status — краткий статус\n"
        "/open_cases — активные кейсы\n"
        "/close_case {id} {comment} — закрыть кейс\n"
        "/cancel_case {id} {reason} — отменить кейс"
    )


async def handle_reload_cars(message: Message, session_factory: async_sessionmaker, settings: Settings) -> None:
    if not _has_bot_access(message, settings):
        await _answer_no_access(message)
        return
    async with session_factory() as session:
        count = await reload_cars_from_excel(session, settings.cars_excel_path)
        await session.commit()
    await message.answer(f"Загружено авто: {count}")


async def handle_status(message: Message, session_factory: async_sessionmaker, settings: Settings) -> None:
    if not _has_bot_access(message, settings):
        await _answer_no_access(message)
        return
    async with session_factory() as session:
        cases = await open_cases(session)
    await message.answer(f"Открытых кейсов: {len(cases)}")


async def handle_open_cases(message: Message, session_factory: async_sessionmaker, settings: Settings) -> None:
    if not _has_bot_access(message, settings):
        await _answer_no_access(message)
        return
    async with session_factory() as session:
        cases = await open_cases(session)
        lines = []
        for case in cases[:30]:
            car = await get_car(session, case.car_id)
            plate = car.original_plate if car else "-"
            lines.append(
                f"#{case.id} {plate} | {case.driver_name or '-'} | {case.manager_name or '-'} | "
                f"{case.status} | {case.reminders_sent}"
            )
    await message.answer("\n".join(lines) if lines else "Открытых кейсов нет.")


async def handle_close_case(message: Message, session_factory: async_sessionmaker, settings: Settings) -> None:
    if not _has_bot_access(message, settings):
        await _answer_no_access(message)
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        await message.answer("Формат: /close_case {case_id} {comment}")
        return
    close_status = classify_close_comment(parts[2])
    if not close_status:
        await message.answer("Комментарий не похож на закрывающий.")
        return
    async with session_factory() as session:
        case = await session.get(DamageCase, int(parts[1]))
        if not case:
            await message.answer("Кейс не найден.")
            return
        _close_case(case, close_status, message.from_user.id if message.from_user else None, parts[2])
        await create_case_action(session, case.id, ActionType.CLOSED_WITH_COMMENT, comment=parts[2])
        await session.commit()
    await message.answer(f"Кейс #{parts[1]} закрыт: {close_status.value}")


async def handle_cancel_case(message: Message, session_factory: async_sessionmaker, settings: Settings) -> None:
    if not _has_bot_access(message, settings):
        await _answer_no_access(message)
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        await message.answer("Формат: /cancel_case {case_id} {reason}")
        return
    async with session_factory() as session:
        case = await session.get(DamageCase, int(parts[1]))
        if not case:
            await message.answer("Кейс не найден.")
            return
        case.status = CaseStatus.INFO_IGNORED.value
        case.close_comment = parts[2]
        await session.commit()
    await message.answer(f"Кейс #{parts[1]} отменен.")


async def handle_message(
    message: Message,
    bot: Bot,
    session_factory: async_sessionmaker,
    settings: Settings,
) -> None:
    text = message.text or message.caption
    if not text:
        return
    if equivalent_chat_ids(settings.fp_chat_id, message.chat.id) and _is_ignored_fp_user(message, settings):
        logger.info("Ignored FP message from service user %s", message.from_user.username if message.from_user else None)
        return
    if message.from_user:
        await _try_close_waiting_comment(message, session_factory, text)

    if equivalent_chat_ids(settings.fp_chat_id, message.chat.id):
        await _handle_fp_message(message, bot, session_factory, settings, text)
    elif equivalent_chat_ids(settings.pv_chat_id, message.chat.id):
        await _handle_pv_message(message, bot, session_factory, settings, text)


async def handle_callback(callback: CallbackQuery, bot: Bot, session_factory: async_sessionmaker) -> None:
    if not callback.data or not callback.from_user:
        return
    action, raw_case_id = callback.data.split(":", 1)
    async with session_factory() as session:
        case = await session.get(DamageCase, int(raw_case_id))
        if not case:
            await callback.answer("Кейс не найден.", show_alert=True)
            return
        if action == "seen":
            case.status = CaseStatus.MANAGER_SEEN.value
            await create_case_action(
                session,
                case.id,
                ActionType.MANAGER_SEEN,
                callback.from_user.id,
                callback.from_user.username,
                callback.from_user.full_name,
            )
            await session.commit()
            await callback.answer("Отмечено. Напоминания продолжатся до закрытия.")
        elif action == "request_close":
            case.status = CaseStatus.WAITING_CLOSE_COMMENT.value
            case.closed_by_user_id = callback.from_user.id
            await create_case_action(session, case.id, ActionType.CLOSE_REQUESTED, callback.from_user.id)
            await session.commit()
            await callback.message.answer(
                close_comment_prompt(callback.from_user.username),
                reply_markup=ForceReply(selective=True),
            )
            await callback.answer("Жду комментарий.")
        elif action == "close_no_charge":
            case.status = CaseStatus.CLOSED_NO_CHARGE_REQUIRED.value
            case.closed_by_user_id = callback.from_user.id
            case.closed_at = callback.message.date
            case.close_type = CaseStatus.CLOSED_NO_CHARGE_REQUIRED.value
            await create_case_action(
                session,
                case.id,
                ActionType.CLOSED_NO_CHARGE_REQUIRED,
                callback.from_user.id,
                callback.from_user.username,
                callback.from_user.full_name,
            )
            await session.commit()
            await callback.answer("Закрыто.")
            await callback.message.answer(f"Кейс #{case.id} закрыт: списание не требуется.")


async def _handle_fp_message(
    message: Message,
    bot: Bot,
    session_factory: async_sessionmaker,
    settings: Settings,
    text: str,
) -> None:
    parsed = parse_fp_message(text)
    async with session_factory() as session:
        if await find_fp_message(session, message.chat.id, message.message_id):
            return
        cars = await car_refs(session)
        car_match = match_car(parsed.plate_raw, cars)
        car_id = car_match.car.id if car_match.status == MatchStatus.MATCHED and car_match.car else None
        fp = FPMessage(
            telegram_message_id=message.message_id,
            chat_id=message.chat.id,
            sender_id=message.from_user.id if message.from_user else None,
            sender_username=message.from_user.username if message.from_user else None,
            sender_name=message.from_user.full_name if message.from_user else None,
            text=text,
            normalized_text=text.lower().replace("ё", "е"),
            plate_raw=parsed.plate_raw,
            plate_normalized=parsed.plate_normalized,
            car_id=car_id,
            category=parsed.category.value,
            description=parsed.description,
            has_media=int(bool(message.photo or message.video or message.document)),
            created_at=message.date.astimezone(timezone.utc),
        )
        session.add(fp)
        await session.flush()
        if parsed.category in {MessageCategory.DAMAGE_CHARGE_REQUIRED, MessageCategory.DAMAGE_NO_CHARGE_REQUIRED}:
            if car_match.status != MatchStatus.MATCHED:
                await _send_diagnostic(bot, settings, text, parsed.plate_raw, car_match)
            else:
                await create_damage_case_from_fp(session, fp)
        await session.commit()
    logger.info("Parsed FP message %s as %s", message.message_id, parsed.category)


async def _handle_pv_message(
    message: Message,
    bot: Bot,
    session_factory: async_sessionmaker,
    settings: Settings,
    text: str,
) -> None:
    parsed = parse_pv_return(text)
    if not parsed.is_return:
        return
    async with session_factory() as session:
        if await find_pv_return(session, message.chat.id, message.message_id):
            return
        cars = await car_refs(session)
        car_match = match_car(parsed.plate_raw, cars)
        if car_match.status != MatchStatus.MATCHED or not car_match.car:
            await _send_diagnostic(bot, settings, text, parsed.plate_raw, car_match)
            car_id = None
        else:
            car_id = car_match.car.id
        pv = PVReturn(
            telegram_message_id=message.message_id,
            chat_id=message.chat.id,
            text=text,
            operation_type=parsed.operation_type,
            plate_raw=parsed.plate_raw,
            plate_normalized=parsed.plate_normalized,
            car_id=car_id,
            driver_name=parsed.driver_name,
            manager_name=parsed.manager_name,
            balance=parsed.balance,
            deposit=parsed.deposit,
            reason=parsed.reason,
            created_at=message.date.astimezone(timezone.utc),
        )
        session.add(pv)
        await session.flush()
        if car_id:
            cases = await open_cases_for_return(session, car_id, pv.created_at)
            await attach_return_to_cases(session, pv, cases, settings.reminder_first_delay_minutes)
        await session.commit()
    logger.info("Parsed PV return %s for plate %s", message.message_id, parsed.plate_normalized)


async def _try_close_waiting_comment(message: Message, session_factory: async_sessionmaker, text: str) -> None:
    user = message.from_user
    if not user:
        return
    async with session_factory() as session:
        case = await waiting_comment_case_for_user(session, user.id)
        if not case:
            return
        status = classify_close_comment(text)
        if not status:
            await message.reply("Комментарий не закрывает кейс. Нужна оплата/списание/рассрочка/офис/причина без списания.")
            return
        _close_case(case, status, user.id, text)
        await create_case_action(session, case.id, ActionType.CLOSED_WITH_COMMENT, user.id, user.username, user.full_name, text)
        await session.commit()
    await message.reply(f"Кейс #{case.id} закрыт: {status.value}")


def _close_case(case: DamageCase, status: CaseStatus, user_id: int | None, comment: str) -> None:
    case.status = status.value
    case.closed_by_user_id = user_id
    case.close_comment = comment
    case.close_type = status.value
    case.closed_at = utcnow()


async def _send_diagnostic(bot: Bot, settings: Settings, text: str, plate: str | None, car_match) -> None:
    if not settings.admin_chat_id:
        return
    candidates = [
        f"{car.brand or ''} {car.model or ''} {car.original_plate}".strip()
        for car in getattr(car_match, "candidates", ())
    ]
    await bot.send_message(
        settings.admin_chat_id,
        diagnostic_text(text, plate, car_match.status.value, candidates),
    )


async def _answer_no_access(message: Message) -> None:
    await message.answer("Не лезь куда не надо 😄 Тут кнопки только для Fedos_AV.")


def _has_bot_access(message: Message, settings: Settings) -> bool:
    if not message.from_user:
        return False
    if message.from_user.id in settings.admins:
        return True
    username = (message.from_user.username or "").lstrip("@").lower()
    return username == settings.supervisor_username.lstrip("@").lower()


def _is_ignored_fp_user(message: Message, settings: Settings) -> bool:
    username = message.from_user.username if message.from_user else None
    return bool(username and username.lower() in settings.ignored_fp_usernames)
