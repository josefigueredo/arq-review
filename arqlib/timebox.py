"""Business-day timebox for waiting on the requester (spec D7). Weekends only; holidays are out of scope."""
from __future__ import annotations

from datetime import date, timedelta


class TimeboxError(ValueError):
    pass


def add_business_days(start: date, days: int) -> date:
    if days < 1:
        raise TimeboxError("el plazo tiene que ser de al menos 1 día hábil")
    current, counted = start, 0
    while counted < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            counted += 1
    return current


def is_overdue(vence: str, today: date) -> bool:
    try:
        due = date.fromisoformat(vence)
    except ValueError as exc:
        raise TimeboxError(f"fecha inválida {vence!r}: usar AAAA-MM-DD") from exc
    return today > due
