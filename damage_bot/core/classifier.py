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

DAMAGE_PATTERNS = [
    r"поврежд",
    r"царапин",
    r"помят",
    r"разбит",
    r"\bдтп\b",
    r"трещин",
    r"скол",
    r"вмятин",
    r"удар",
    r"бампер",
    r"двер",
]

SERVICE_PATTERNS = [
    r"слесарк",
    r"\bто\b",
    r"подошло\s+то",
    r"вед[её]т\s+вправо",
    r"ремонт",
    r"диагностик",
    r"ошибк",
    r"горит\s+ошибк",
]

CLEANING_PATTERNS = [
    r"пылесос",
    r"пропылесос",
    r"ковр",
    r"мойк",
    r"помыл",
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
    if _matches(SERVICE_PATTERNS, normalized):
        return MessageCategory.SERVICE_IGNORED
    if _matches(CLEANING_PATTERNS, normalized):
        return MessageCategory.CLEANING_IGNORED
    if _matches(NO_CHARGE_PATTERNS, normalized):
        return MessageCategory.DAMAGE_NO_CHARGE_REQUIRED
    if _matches(DAMAGE_PATTERNS, normalized):
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

