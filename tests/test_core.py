from datetime import datetime, timezone

from damage_bot.core.classifier import classify_close_comment, classify_fp_text
from damage_bot.core.constants import CaseStatus, MessageCategory
from damage_bot.core.matching import CarRef, MatchStatus, match_car
from damage_bot.core.parsers import parse_fp_message, parse_pv_return
from damage_bot.core.plates import digits_key, equivalent_chat_ids, normalize_plate
from damage_bot.core.workflow import ReminderSchedule, escalation_due_at, reminder_due_at


def test_plate_normalization() -> None:
    assert normalize_plate("о917нх797") == "O917HX797"
    assert normalize_plate("с771сн761") == "C771CH761"
    assert normalize_plate("т553нм797") == "T553HM797"


def test_digits_key() -> None:
    assert digits_key("O917HX797") == "917797"




def test_equivalent_chat_ids_supports_supergroup_formats() -> None:
    assert equivalent_chat_ids(1001905865504, -1001905865504)
    assert equivalent_chat_ids(-1001941984098, 1001941984098)

def test_fp_parser_damage_no_charge() -> None:
    parsed = parse_fp_message(
        "О917нх797 сдал\n"
        "29.05.26 было дтп, вт не виноват, постановление отправил в офис.\n"
        "Повреждения: дверь передняя левая (помята)"
    )
    assert parsed.plate_normalized == "O917HX797"
    assert parsed.category == MessageCategory.DAMAGE_NO_CHARGE_REQUIRED
    assert "постановление" in parsed.description


def test_fp_parser_regular_damage() -> None:
    parsed = parse_fp_message("у916не797 сдал\nПоврежден передний бампер справа")
    assert parsed.plate_normalized == "Y916HE797"
    assert parsed.category == MessageCategory.DAMAGE_CHARGE_REQUIRED


def test_fp_ignores_service_and_cleaning_from_screenshots() -> None:
    assert classify_fp_text("т579нм797\nВ слесарке") == MessageCategory.SERVICE_IGNORED
    assert classify_fp_text("С771сн761 сдал\nСильно ведет вправо") == MessageCategory.SERVICE_IGNORED
    assert classify_fp_text("О864оа797 сдал\nПылесосит и моет коврики") == MessageCategory.CLEANING_IGNORED


def test_pv_parser_extracts_return_fields() -> None:
    parsed = parse_pv_return(
        "🟥 Аренда | Сдача EXEED LX о917нх797\n\n"
        "Водитель: Курбанмагомедов Шахбан Курбанмагомедович\n"
        "Баланс (в т.ч. 1С): 1 004\n"
        "Сводный баланс: 0\n"
        "Депозит: 24 900\n\n"
        "Причина: Другое - не хочет пока работать в такси\n\n"
        "Сотрудник: Губайдуллин Рафаэль\n\n"
        "Водитель отработал 18 дней"
    )
    assert parsed.is_return
    assert parsed.operation_type == "Сдача"
    assert parsed.plate_normalized == "O917HX797"
    assert parsed.car_model == "EXEED LX"
    assert parsed.driver_name == "Курбанмагомедов Шахбан Курбанмагомедович"
    assert parsed.manager_name == "Губайдуллин Рафаэль"
    assert parsed.deposit == "24 900"


def test_pv_parser_ignores_non_return() -> None:
    assert not parse_pv_return("Аренда | Выдача Kia Rio к244он761").is_return


def test_pv_parser_accepts_reseating_as_return_event() -> None:
    parsed = parse_pv_return(
        "🟥 Аренда | Пересадка Kia K5 с771сн761\n\n"
        "Водитель: Иванов Евгений Александрович\n"
        "Сотрудник: Губайдуллин Рафаэль"
    )
    assert parsed.is_return
    assert parsed.operation_type == "Пересадка"
    assert parsed.plate_normalized == "C771CH761"
    assert parsed.driver_name == "Иванов Евгений Александрович"


def test_car_matching_exact_digits_unknown_and_ambiguous() -> None:
    cars = [
        CarRef(1, "EXEED", "LX", "О917НХ797", "O917HX797", "917797"),
        CarRef(2, "Kia", "K5", "С771СН761", "C771CH761", "771761"),
        CarRef(3, "Kia", "Rio", "К771ОН761", "K771OH761", "771761"),
    ]
    assert match_car("O917HX797", cars).status == MatchStatus.MATCHED
    assert match_car("о917нх797", cars).car.id == 1
    assert match_car("A771AA761", cars).status == MatchStatus.AMBIGUOUS
    assert match_car("A000AA000", cars).status == MatchStatus.UNKNOWN


def test_reminder_schedule() -> None:
    returned_at = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    schedule = ReminderSchedule(first_delay_minutes=10, interval_minutes=30, max_reminders=3)
    assert reminder_due_at(returned_at, 0, schedule).minute == 10
    assert reminder_due_at(returned_at, 1, schedule).minute == 40
    assert reminder_due_at(returned_at, 2, schedule).hour == 11
    assert reminder_due_at(returned_at, 2, schedule).minute == 10
    assert escalation_due_at(returned_at, schedule).hour == 11
    assert escalation_due_at(returned_at, schedule).minute == 40


def test_closing_comment_classification() -> None:
    assert classify_close_comment("оплатил 20000 наличными") == CaseStatus.CLOSED_PAID_CASH
    assert classify_close_comment("списали 15000 с баланса") == CaseStatus.CLOSED_BALANCE_CHARGED
    assert classify_close_comment("поставили рассрочку 30000") == CaseStatus.CLOSED_INSTALLMENT
    assert classify_close_comment("ок") is None
