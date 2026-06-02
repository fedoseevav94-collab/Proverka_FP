from damage_bot.core.constants import MessageCategory
from damage_bot.core.buttons import reminder_button_specs


def test_no_charge_keyboard_has_only_confirmation_button() -> None:
    buttons = reminder_button_specs(42, MessageCategory.DAMAGE_NO_CHARGE_REQUIRED.value)
    assert len(buttons) == 1
    assert buttons[0].text == "🔎 Проверено без списания"
    assert buttons[0].callback_data == "close_no_charge:42"


def test_regular_damage_keyboard_has_pv_action_buttons() -> None:
    buttons = reminder_button_specs(42, MessageCategory.DAMAGE_CHARGE_REQUIRED.value)
    texts = [button.text for button in buttons]
    assert texts == ["💰 Оплата / списание", "☑️ Без списания"]
