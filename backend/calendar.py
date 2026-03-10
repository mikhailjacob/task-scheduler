"""Calendar date computation for schedule display."""

from __future__ import annotations

from datetime import date, timedelta

from .models import CalendarSettings


def compute_calendar_dates(
    settings: CalendarSettings, total_days: int
) -> list[date]:
    """Compute a list of calendar dates for each working day.

    Args:
        settings: Calendar configuration (start date, weekend handling).
        total_days: Number of working days to map.

    Returns:
        A list of ``total_days`` date objects.
    """
    if total_days <= 0:
        return []

    dates: list[date] = []
    current = settings.start_date

    # If weekdays only and start is on a weekend, advance to Monday
    if not settings.show_weekends:
        while current.weekday() >= 5:
            current += timedelta(days=1)

    while len(dates) < total_days:
        if settings.show_weekends or current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)

    return dates
