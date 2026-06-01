from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from damage_bot.core.managers import active_manager_mentions

OFFICE_START = time(9, 30)
OFFICE_END = time(18, 30)
NEXT_DAY_REMINDER_TIME = time(9, 45)


def fp_first_due_at(
    created_at: datetime,
    delay_minutes: int,
    manager_days_off: str,
    timezone_name: str = "Europe/Moscow",
) -> datetime:
    tz = ZoneInfo(timezone_name)
    local_created = created_at.astimezone(tz)
    regular_due = local_created + timedelta(minutes=delay_minutes)

    if _inside_office_day(local_created) and regular_due.time() <= OFFICE_END:
        return regular_due.astimezone(created_at.tzinfo or tz)

    next_local_due = _next_active_manager_morning(
        local_created.date() + timedelta(days=1),
        manager_days_off,
        tz,
    )
    return next_local_due.astimezone(created_at.tzinfo or tz)


def _inside_office_day(value: datetime) -> bool:
    return OFFICE_START <= value.time() <= OFFICE_END


def _next_active_manager_morning(start_date, manager_days_off: str, tz: ZoneInfo) -> datetime:
    current = start_date
    for _ in range(14):
        candidate = datetime.combine(current, NEXT_DAY_REMINDER_TIME, tzinfo=tz)
        mentions = active_manager_mentions(manager_days_off, candidate.weekday())
        if mentions and mentions != "Менеджеры":
            return candidate
        current += timedelta(days=1)
    return datetime.combine(start_date, NEXT_DAY_REMINDER_TIME, tzinfo=tz)
