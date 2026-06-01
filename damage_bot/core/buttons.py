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
                text="✅ Проверено, списание не требуется",
                callback_data=f"close_no_charge:{case_id}",
            )
        ]
    return [
        ButtonSpec(text="⏳ Жду сумму от @Norblacksmith", callback_data=f"wait_service_amount:{case_id}"),
        ButtonSpec(text="✅ Водитель оплатил", callback_data=f"request_paid:{case_id}"),
        ButtonSpec(text="✅ Списание не требуется", callback_data=f"close_no_charge:{case_id}"),
    ]

