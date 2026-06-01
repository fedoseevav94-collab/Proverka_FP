from __future__ import annotations

from pathlib import Path


def resolve_cars_excel_path(path: str) -> Path:
    requested = Path(path)
    if requested.exists():
        return requested

    parent = requested.parent if str(requested.parent) else Path(".")
    if parent.exists():
        candidates = sorted(
            parent.glob("Парковые авто*.xlsx"),
            key=lambda candidate: candidate.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            return candidates[0]

    raise FileNotFoundError(
        f"Не найден файл: {requested}. "
        f"Также проверил автопоиск: {parent / 'Парковые авто*.xlsx'}"
    )
