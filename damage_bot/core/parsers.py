from __future__ import annotations

import re
from dataclasses import dataclass

from damage_bot.core.classifier import classify_fp_text
from damage_bot.core.constants import MessageCategory
from damage_bot.core.plates import find_plate, normalize_plate


@dataclass(frozen=True)
class ParsedFPMessage:
    plate_raw: str | None
    plate_normalized: str
    category: MessageCategory
    description: str


@dataclass(frozen=True)
class ParsedPVReturn:
    is_return: bool
    operation_type: str | None = None
    plate_raw: str | None = None
    plate_normalized: str = ""
    car_model: str | None = None
    driver_name: str | None = None
    manager_name: str | None = None
    balance: str | None = None
    deposit: str | None = None
    reason: str | None = None


def parse_fp_message(text: str) -> ParsedFPMessage:
    plate_raw = find_plate(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    description_lines = lines[1:] if lines and plate_raw and plate_raw in lines[0] else lines
    description = "\n".join(description_lines).strip() or text.strip()
    return ParsedFPMessage(
        plate_raw=plate_raw,
        plate_normalized=normalize_plate(plate_raw),
        category=classify_fp_text(text),
        description=description,
    )


def parse_pv_return(text: str) -> ParsedPVReturn:
    operation_match = re.search(r"аренда\s*\|\s*(сдача|пересадка)", text, re.IGNORECASE)
    if not operation_match:
        return ParsedPVReturn(is_return=False)

    operation_type = operation_match.group(1).capitalize()
    plate_raw = find_plate(text)
    title_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    car_model = None
    if plate_raw and title_line:
        car_part = re.sub(r"^.*?аренда\s*\|\s*(сдача|пересадка)", "", title_line, flags=re.IGNORECASE)
        car_model = car_part.replace(plate_raw, "").strip(" -|")

    return ParsedPVReturn(
        is_return=True,
        operation_type=operation_type,
        plate_raw=plate_raw,
        plate_normalized=normalize_plate(plate_raw),
        car_model=car_model or None,
        driver_name=_field(text, "Водитель"),
        manager_name=_field(text, "Сотрудник"),
        balance=_field(text, "Баланс \\(в т\\.ч\\. 1С\\)") or _field(text, "Баланс"),
        deposit=_field(text, "Депозит"),
        reason=_field(text, "Причина"),
    )


def _field(text: str, label_pattern: str) -> str | None:
    match = re.search(rf"^{label_pattern}\s*:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else None


def is_fp_inspection(text: str) -> bool:
    return bool(re.search(r"\bосмотр\w*", text.lower().replace("ё", "е"), re.IGNORECASE))


def parse_pv_issue(text: str) -> ParsedPVReturn:
    operation_match = re.search(r"аренда\s*\|\s*выдача", text, re.IGNORECASE)
    if not operation_match:
        return ParsedPVReturn(is_return=False)
    plate_raw = find_plate(text)
    title_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    car_model = None
    if plate_raw and title_line:
        car_part = re.sub(r"^.*?аренда\s*\|\s*выдача", "", title_line, flags=re.IGNORECASE)
        car_model = car_part.replace(plate_raw, "").strip(" -|")
    return ParsedPVReturn(
        is_return=False,
        operation_type="Выдача",
        plate_raw=plate_raw,
        plate_normalized=normalize_plate(plate_raw),
        car_model=car_model or None,
        driver_name=_field(text, "Водитель"),
        manager_name=_field(text, "Сотрудник"),
        balance=_field(text, r"Баланс \(в т\.ч\. 1С\)") or _field(text, "Баланс"),
        deposit=_field(text, "Депозит"),
        reason=_field(text, "Причина"),
    )
