WEEKDAY_ALIASES = {
    "mon": 0,
    "monday": 0,
    "пн": 0,
    "tue": 1,
    "tuesday": 1,
    "вт": 1,
    "wed": 2,
    "wednesday": 2,
    "ср": 2,
    "thu": 3,
    "thursday": 3,
    "чт": 3,
    "fri": 4,
    "friday": 4,
    "пт": 4,
    "sat": 5,
    "saturday": 5,
    "сб": 5,
    "sun": 6,
    "sunday": 6,
    "вс": 6,
}


def parse_manager_days_off(raw: str) -> dict[str, set[int]]:
    result: dict[str, set[int]] = {}
    for block in raw.split(";"):
        if not block.strip() or ":" not in block:
            continue
        username, days = block.split(":", 1)
        parsed_days = {
            WEEKDAY_ALIASES[item.strip().lower()]
            for item in days.split(",")
            if item.strip().lower() in WEEKDAY_ALIASES
        }
        result[username.strip().lstrip("@").lower()] = parsed_days
    return result


def active_manager_mentions(raw_days_off: str, weekday: int) -> str | None:
    days_off = parse_manager_days_off(raw_days_off)
    if not days_off:
        return None
    mentions = [
        f"@{username}"
        for username, off_days in days_off.items()
        if weekday not in off_days
    ]
    return " ".join(mentions) if mentions else "Менеджеры"


def parse_manager_directory(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for block in raw.split(";"):
        if not block.strip() or ":" not in block:
            continue
        username, full_name = block.split(":", 1)
        username = username.strip().lstrip("@").lower()
        full_name = full_name.strip()
        if username and full_name:
            result[username] = full_name
    return result


def infer_manager_username(manager_name: str | None, raw_directory: str) -> str | None:
    if not manager_name:
        return None
    query_tokens = _name_tokens(manager_name)
    if not query_tokens:
        return None
    matches = []
    for username, full_name in parse_manager_directory(raw_directory).items():
        known_tokens = _name_tokens(full_name)
        if query_tokens.issubset(known_tokens):
            matches.append(username)
            continue
        if len(query_tokens) >= 2 and len(query_tokens & known_tokens) >= 2:
            matches.append(username)
    return matches[0] if len(set(matches)) == 1 else None


def _name_tokens(value: str) -> set[str]:
    cleaned = value.lower().replace("ё", "е")
    return {part for part in cleaned.replace("-", " ").split() if len(part) > 1}
