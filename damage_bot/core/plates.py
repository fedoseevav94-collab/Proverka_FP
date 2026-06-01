from __future__ import annotations

import re


CYRILLIC_TO_LATIN = str.maketrans(
    {
        "А": "A",
        "В": "B",
        "Е": "E",
        "К": "K",
        "М": "M",
        "Н": "H",
        "О": "O",
        "Р": "P",
        "С": "C",
        "Т": "T",
        "У": "Y",
        "Х": "X",
        "Ё": "E",
    }
)

PLATE_RE = re.compile(
    r"(?<![A-ZА-ЯЁ0-9])([АВЕКМНОРСТУХABEKMHOPCTYX]\s*[-.]?\s*\d{3}\s*[-.]?\s*[АВЕКМНОРСТУХABEKMHOPCTYX]{2}\s*[-.]?\s*\d{2,3})(?![A-ZА-ЯЁ0-9])",
    re.IGNORECASE,
)


def normalize_plate(value: str | None) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"[\s.\-]+", "", value.upper().replace("Ё", "Е"))
    return cleaned.translate(CYRILLIC_TO_LATIN)


def digits_key(value: str | None) -> str:
    return "".join(re.findall(r"\d", normalize_plate(value)))


def find_plate(text: str | None) -> str | None:
    if not text:
        return None
    match = PLATE_RE.search(text)
    return match.group(1) if match else None


def equivalent_chat_ids(configured: int, incoming: int) -> bool:
    if configured == incoming:
        return True
    configured_s = str(configured)
    incoming_s = str(incoming)
    return configured_s.removeprefix("-100") == incoming_s.removeprefix("-100")


def make_message_link(chat_id: int, message_id: int) -> str:
    chat_s = str(chat_id)
    internal_id = chat_s.removeprefix("-100")
    if internal_id.startswith("100"):
        internal_id = internal_id[3:]
    if internal_id and internal_id.lstrip("-").isdigit():
        return f"https://t.me/c/{internal_id}/{message_id}"
    return f"chat_id={chat_id}, message_id={message_id}"

