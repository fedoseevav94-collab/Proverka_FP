from __future__ import annotations

from zoneinfo import ZoneInfo

from damage_bot.core.constants import CaseStatus, MessageCategory
from damage_bot.core.plates import make_message_link
from damage_bot.db import DamageCase


def reminder_text(case: DamageCase, mention_override: str | None = None) -> str:
    mention = mention_override or (f"@{case.manager_username}" if case.manager_username else (case.manager_name or "Менеджер"))
    car = case.car
    plate = car.original_plate if car else ""
    if case.category == MessageCategory.DAMAGE_NO_CHARGE_REQUIRED.value:
        return (
            f"{mention}\n\n"
            f"По авто {plate} есть сообщение в ФП.\n\n"
            f"Авто: {_car_label(case)}\n"
            f"Водитель: {case.driver_name or '-'}\n"
            f"Менеджер: {case.manager_name or '-'}\n\n"
            "В сообщении указано, что водитель не виноват / документы переданы в офис.\n\n"
            f"Описание:\n{case.damage_description}\n\n"
            "Списание не требуется, но нужно подтвердить, что сообщение проверено.\n\n"
            f"Напоминание {case.reminders_sent + 1}/3."
        )
    return (
        f"{mention}\n\n"
        f"По авто {plate} есть зафиксированное повреждение в ФП.\n\n"
        f"Авто: {_car_label(case)}\n"
        f"Водитель: {case.driver_name or '-'}\n"
        f"Менеджер: {case.manager_name or '-'}\n\n"
        f"Повреждение:\n{case.damage_description}\n\n"
        "Машина уже сдана в ПВ.\n"
        "Нужно закрыть вопрос по списанию:\n"
        "— оплатил наличными;\n"
        "— списали с баланса;\n"
        "— поставили рассрочку;\n"
        "— передано в офис;\n"
        "— списание не требуется, причина.\n\n"
        f"Напоминание {case.reminders_sent + 1}/3."
    )


def close_comment_prompt(manager: str | None) -> str:
    target = f"@{manager}" if manager else "Менеджер"
    return (
        f"{target}, напишите комментарий по закрытию.\n\n"
        "Примеры:\n"
        "— оплатил 20000 наличными\n"
        "— списали 15000 с баланса\n"
        "— поставили рассрочку 30000\n"
        "— передано в офис\n"
        "— списание не требуется, причина"
    )


def escalation_text(case: DamageCase) -> str:
    fp_link = make_message_link(case.fp_message.chat_id, case.fp_message.telegram_message_id)
    pv_link = (
        make_message_link(case.pv_return.chat_id, case.pv_return.telegram_message_id)
        if case.pv_return
        else "-"
    )
    return (
        "Менеджер не закрыл повреждение после 3 напоминаний.\n\n"
        f"Авто: {_car_label(case)}\n"
        f"Водитель: {case.driver_name or '-'}\n"
        f"Менеджер: {case.manager_name or '-'}\n\n"
        f"Повреждение:\n{case.damage_description}\n\n"
        f"Категория: {case.category}\n"
        f"Статус: {case.status}\n"
        "Напоминаний отправлено: 3\n\n"
        f"Сообщение ФП: {fp_link}\n"
        f"Сообщение ПВ: {pv_link}"
    )


def diagnostic_text(text: str, plate: str | None, reason: str, candidates: list[str] | None = None) -> str:
    candidate_text = "\n".join(candidates or []) or "-"
    return (
        "Не удалось однозначно определить автомобиль.\n\n"
        f"Причина: {reason}\n"
        f"Текст: {text[:1500]}\n"
        f"Найденный номер: {plate or '-'}\n"
        f"Похожие варианты:\n{candidate_text}\n\n"
        "Нужна ручная проверка."
    )


def status_label(status: CaseStatus | str) -> str:
    return status.value if isinstance(status, CaseStatus) else status


def _car_label(case: DamageCase) -> str:
    car = case.car
    if not car:
        return "-"
    return " ".join(part for part in [car.brand, car.model, car.original_plate] if part)



def _workflow_context(case: DamageCase) -> str:
    if case.pv_return_id:
        return "Машина уже сдана в ПВ."
    return "После осмотра в ФП нужно закрыть вопрос по повреждению."


def service_amount_request_text(case: DamageCase, service_username: str) -> str:
    return (
        f"@{service_username.lstrip('@')} нужна оценка/сумма по повреждению.\n\n"
        f"Авто: {_car_label(case)}\n"
        "Описание и фото в сообщении, на которое я отвечаю.\n\n"
        "Ответьте reply к этому сообщению или к исходному ФП-сообщению."
    )


def pv_action_request_text(case: DamageCase, mention_override: str | None = None) -> str:
    mention = f"{mention_override}\n\n" if mention_override else ""
    details = []
    if case.driver_name:
        details.append(f"Водитель: {case.driver_name}")
    if case.manager_name:
        details.append(f"Менеджер: {case.manager_name}")
    detail_text = "\n".join(details)
    if detail_text:
        detail_text += "\n\n"
    return (
        mention
        + f"Найдены повреждения по авто {_car_label(case)}.\n"
        + f"{_workflow_context(case)}\n\n"
        + detail_text
        + "@Norblacksmith уже запрошен для оценки/суммы.\n"
        "Выберите действие после проверки."
    )


def close_summary_text(
    case: DamageCase,
    status: CaseStatus,
    actor: str | None,
    comment: str | None = None,
    timezone_name: str = "Europe/Moscow",
) -> str:
    car = case.car
    plate = car.original_plate if car else "-"
    action = _close_action_label(status)
    inspected_at = "-"
    if case.fp_message and case.fp_message.created_at:
        inspected_at = case.fp_message.created_at.astimezone(ZoneInfo(timezone_name)).strftime("%d.%m.%Y %H:%M")
    lines = [
        f"Сотрудник {actor or '-'} {action} по повреждениям на авто {plate}.",
        f"Дата и время осмотра: {inspected_at}",
    ]
    if comment:
        lines.append(f"Комментарий: {comment}")
    return "\n".join(lines)


def _close_action_label(status: CaseStatus) -> str:
    labels = {
        CaseStatus.CLOSED_PAID_CASH: "зафиксировал оплату",
        CaseStatus.CLOSED_BALANCE_CHARGED: "зафиксировал списание с баланса/депозита",
        CaseStatus.CLOSED_INSTALLMENT: "поставил рассрочку",
        CaseStatus.CLOSED_PERIODIC_CHARGES: "поставил периодические списания",
        CaseStatus.CLOSED_TRANSFERRED_TO_OFFICE: "передал вопрос в офис",
        CaseStatus.CLOSED_NO_CHARGE_REQUIRED: "подтвердил, что списание не требуется",
        CaseStatus.CLOSED_NO_CHARGE_WITH_REASON: "закрыл без списания",
    }
    return labels.get(status, f"закрыл кейс ({status.value})")
