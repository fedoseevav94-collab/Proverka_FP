from __future__ import annotations

from dataclasses import dataclass

from damage_bot.core.constants import MessageCategory


@dataclass(frozen=True)
class ButtonSpec:
    text: str
    callback_data: str


def reminder_button_specs(case_id: int, category: str) -> list[ButtonSpec]:
    if category == MessageCategory.DAMAGE_NO_CHARGE_REQUIRED.value:
        return [
            ButtonSpec(
                text="🔎 Проверено без списания",
                callback_data=f"close_no_charge:{case_id}",
            )
        ]
    return [
        ButtonSpec(text="💰 Оплата / списание", callback_data=f"request_paid:{case_id}"),
        ButtonSpec(text="☑️ Без списания", callback_data=f"close_no_charge:{case_id}"),
    ]
