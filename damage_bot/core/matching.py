from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from damage_bot.core.plates import digits_key, normalize_plate


class MatchStatus(StrEnum):
    MATCHED = "MATCHED"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CarRef:
    id: int | None
    brand: str | None
    model: str | None
    original_plate: str
    normalized_plate: str
    digits_key: str


@dataclass(frozen=True)
class CarMatch:
    status: MatchStatus
    car: CarRef | None = None
    candidates: tuple[CarRef, ...] = ()


def match_car(plate: str | None, cars: list[CarRef]) -> CarMatch:
    normalized = normalize_plate(plate)
    if not normalized:
        return CarMatch(status=MatchStatus.UNKNOWN)

    for car in cars:
        if car.normalized_plate == normalized:
            return CarMatch(status=MatchStatus.MATCHED, car=car)

    key = digits_key(normalized)
    candidates = tuple(car for car in cars if car.digits_key == key)
    if len(candidates) == 1:
        return CarMatch(status=MatchStatus.MATCHED, car=candidates[0])
    if len(candidates) > 1:
        return CarMatch(status=MatchStatus.AMBIGUOUS, candidates=candidates)
    return CarMatch(status=MatchStatus.UNKNOWN)


def match_car_exact(plate: str | None, cars: list[CarRef]) -> CarMatch:
    normalized = normalize_plate(plate)
    if not normalized:
        return CarMatch(status=MatchStatus.UNKNOWN)

    candidates = tuple(car for car in cars if car.normalized_plate == normalized)
    if len(candidates) == 1:
        return CarMatch(status=MatchStatus.MATCHED, car=candidates[0])
    if len(candidates) > 1:
        return CarMatch(status=MatchStatus.AMBIGUOUS, candidates=candidates)
    return CarMatch(status=MatchStatus.UNKNOWN)
