from __future__ import annotations

import re

from damage_bot.core.constants import CaseStatus, MessageCategory


NO_CHARGE_PATTERNS = [
    r"водител[ья]\s+не\s+виноват",
    r"\bвт\s+не\s+виноват",
    r"\bне\s+виноват",
    r"постановлени[ея]\s+отправил",
    r"постановлени[ея]\s+отправлен[оа]",
    r"передан[оа]?\s+в\s+офис",
]

STRONG_DAMAGE_PATTERNS = [
    r"поврежд",
    r"повредил",
    r"повежд",
    r"царап",
    r"поцарап",
    r"счесан",
    r"помят",
    r"замят",
    r"смят",
    r"вмят",
    r"разбит",
    r"разбил",
    r"\bдтп\b",
    r"трещ",
    r"тресн",
    r"стезин",
    r"лопнул",
    r"лопнув",
    r"скол",
    r"сколот",
    r"удар",
    r"зацеп",
    r"задел",
    r"задир",
    r"зат[её]рт",
    r"зат[её]ртост",
    r"прит[её]р",
    r"прит[её]ртост",
    r"пот[её]рт",
    r"пот[её]ртост",
    r"содран",
    r"ободран",
    r"сорван",
    r"слом",
    r"сломан",
    r"отлом",
    r"оторван",
    r"отош[её]л",
    r"слетел",
    r"выпал",
    r"деформ",
    r"погнут",
    r"пробит",
    r"пробил",
    r"прокол",
    r"проколот",
    r"порез",
    r"порван",
    r"прожжен",
    r"прокур",
    r"курени",
    r"пахнет\s+(?:сигарет|табак|курев)",
    r"запах(?:а|ом)?\s+(?:сигарет|табак|курев)",
    r"не\s*приятн\w*\s+запах",
    r"запах\s+в\s+(?:багажник|салон|машин)",
    r"устран\w*\s+запах",
    r"воня(?:ет|ло|ла|ли)",
    r"пепл",
    r"дыр",
    r"грыж",
    r"спуска[ею]т",
    r"спущен",
    r"саморез",
    r"шуруп",
    r"гвозд",
    r"бордюр",
    r"бордюрк",
    r"нет\s+(?:запасн|колес|диск|молдинг|накладк|подкрыл|колпак|заглушк|рамк|номер|букв|эмблем|лючок|крышк|полк|крюк)",
    r"отсутств(?:ует|уют)\s+(?:молдинг|накладк|подкрыл|колпак|заглушк|рамк|номер|букв|эмблем|лючок|крышк|полк|крюк|треугольник|повторитель|реш[её]тк)",
    r"потер(?:ян|я|ял|яны)",
    r"утерян",
    r"замен[ауы]?\s+(?:лобов|стекл|дворник|трапец|подкрыл|покрыш|резин|шин|колес|диск|радиатор|капот|бампер|крыл)",
    r"(?:лобов|стекл).*менять",
    r"(?:резин|покрыш|шин).*вине\s+водител",
    r"списать\s+за\s+резин",
    r"ремонт\s+(?:колес|шин|покрыш|диск|бампер|стекл|лобов|радиатор|крыл|капот)",
]

DAMAGE_PART_PATTERNS = [
    r"бампер",
    r"двер",
    r"крыл",
    r"капот",
    r"багажник",
    r"порог",
    r"зеркал",
    r"лобов",
    r"фара",
    r"фонар",
    r"птф",
    r"реш[её]тк",
    r"радиатор",
    r"поддон",
    r"молдинг",
    r"накладк",
    r"подкрыл",
    r"арка",
    r"пленк",
    r"пластик",
    r"рамк[аи]\s+(?:гос\s*)?номер",
    r"номерн(?:ой|ого)\s+знак",
    r"гос\s*номер",
    r"диск(?:\s+колес)?",
    r"колес",
    r"покрыш",
    r"шина",
    r"резин",
]

DAMAGE_PATTERNS = STRONG_DAMAGE_PATTERNS + DAMAGE_PART_PATTERNS

SERVICE_PATTERNS = [
    r"слесарк",
    r"(?<!что )(?<!-)\bто\b(?!-)",
    r"подошло\s+то",
    r"вед[её]т\s+вправо",
    r"сход\s*развал",
    r"не\s+работает\s+конд",
    r"акпп",
    r"ходов",
    r"диагностик",
    r"ошибк",
    r"горит\s+ошибк",
    r"ремонт",
]

CLEANING_PATTERNS = [
    r"пылесос",
    r"пропылесос",
    r"ковр",
    r"мойк",
    r"помыл",
    r"грязн",
    r"плохо\s+помыт",
    r"не\s+мыл",
    r"уборк",
    r"химчистк",
]

INVALID_CLOSE_PATTERNS = [
    r"^\s*ок\s*$",
    r"увидел",
    r"принял",
    r"посмотрю",
    r"потом",
    r"разберусь",
    r"в\s+работе",
]


def _matches(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def classify_fp_text(text: str) -> MessageCategory:
    normalized = text.lower().replace("ё", "е")
    if _matches(NO_CHARGE_PATTERNS, normalized):
        return MessageCategory.DAMAGE_NO_CHARGE_REQUIRED
    if _matches(STRONG_DAMAGE_PATTERNS, normalized):
        return MessageCategory.DAMAGE_CHARGE_REQUIRED
    if _matches(SERVICE_PATTERNS, normalized):
        if _matches(DAMAGE_PART_PATTERNS, normalized):
            return MessageCategory.DAMAGE_CHARGE_REQUIRED
        return MessageCategory.SERVICE_IGNORED
    if _matches(CLEANING_PATTERNS, normalized):
        return MessageCategory.CLEANING_IGNORED
    if _matches(DAMAGE_PART_PATTERNS, normalized):
        return MessageCategory.DAMAGE_CHARGE_REQUIRED
    return MessageCategory.INFO_IGNORED


def extract_amount(text: str) -> int | None:
    for match in re.finditer(r"(?<!\d)(\d{1,3}(?:\s\d{3})+|\d{4,7})(?:\s*(?:р|руб\.?))?", text, re.IGNORECASE):
        return int(match.group(1).replace(" ", ""))
    return None


def classify_close_comment(text: str) -> CaseStatus | None:
    normalized = text.lower().replace("ё", "е")
    if _matches(INVALID_CLOSE_PATTERNS, normalized):
        return None
    if re.search(r"списани[ея]\s+не\s+треб", normalized):
        return CaseStatus.CLOSED_NO_CHARGE_WITH_REASON
    if re.search(r"передан[оа]?\s+в\s+офис", normalized):
        return CaseStatus.CLOSED_TRANSFERRED_TO_OFFICE
    if re.search(r"периодическ", normalized):
        return CaseStatus.CLOSED_PERIODIC_CHARGES
    if re.search(r"рассрочк", normalized):
        return CaseStatus.CLOSED_INSTALLMENT
    if re.search(r"списал|списали|удержал|удержали|депозит|баланс", normalized):
        return CaseStatus.CLOSED_BALANCE_CHARGED
    if re.search(r"оплатил|оплачено|взял|взяли|наличн|перевод|qr", normalized):
        return CaseStatus.CLOSED_PAID_CASH
    return None
