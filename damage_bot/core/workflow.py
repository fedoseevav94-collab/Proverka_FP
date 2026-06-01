from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class ReminderSchedule:
    first_delay_minutes: int = 10
    interval_minutes: int = 30
    max_reminders: int = 3


def reminder_due_at(return_detected_at: datetime, reminders_sent: int, schedule: ReminderSchedule) -> datetime:
    if reminders_sent <= 0:
        return return_detected_at + timedelta(minutes=schedule.first_delay_minutes)
    return return_detected_at + timedelta(
        minutes=schedule.first_delay_minutes + schedule.interval_minutes * reminders_sent
    )


def escalation_due_at(return_detected_at: datetime, schedule: ReminderSchedule) -> datetime:
    return return_detected_at + timedelta(
        minutes=schedule.first_delay_minutes + schedule.interval_minutes * schedule.max_reminders
    )

