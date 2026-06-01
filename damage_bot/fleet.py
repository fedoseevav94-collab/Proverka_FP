from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from damage_bot.core.plates import digits_key, normalize_plate
from damage_bot.db import Car


PLATE_COLUMNS = ("гос", "номер", "plate", "госномер")
BRAND_COLUMNS = ("марка", "brand")
MODEL_COLUMNS = ("модель", "model")
OWNER_COLUMNS = ("собственник", "owner", "парк")
STATUS_COLUMNS = ("статус", "status")


async def reload_cars_from_excel(session: AsyncSession, path: str) -> int:
    df = pd.read_excel(Path(path))
    await session.execute(delete(Car))
    count = 0
    for _, row in df.iterrows():
        data = {str(key): _clean(value) for key, value in row.to_dict().items()}
        plate = _pick(data, PLATE_COLUMNS)
        if not plate:
            continue
        normalized = normalize_plate(plate)
        session.add(
            Car(
                brand=_pick(data, BRAND_COLUMNS),
                model=_pick(data, MODEL_COLUMNS),
                original_plate=plate,
                normalized_plate=normalized,
                digits_key=digits_key(normalized),
                owner=_pick(data, OWNER_COLUMNS),
                status=_pick(data, STATUS_COLUMNS),
                raw_excel_row_json=json.dumps(data, ensure_ascii=False),
            )
        )
        count += 1
    await session.flush()
    return count


def _clean(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _pick(row: dict[str, str | None], needles: tuple[str, ...]) -> str | None:
    for column, value in row.items():
        lowered = column.lower()
        if value and any(needle in lowered for needle in needles):
            return value
    return None

