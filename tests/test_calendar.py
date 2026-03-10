"""Tests for Feature 11: Calendar Day Display

Tests for computing calendar dates, weekday-only schedules, and
date formatting.
"""
import pytest
from datetime import date
from backend import (
    CalendarSettings, compute_calendar_dates, parse_config,
)


class TestCalendarSettingsParsing:
    """Tests for parsing calendar config section."""

    def test_calendar_section_parsed(self):
        yaml_str = """
workers: 1
calendar:
  start_date: "2026-03-09"
  show_weekends: false
projects:
  - name: "P1"
    tasks:
      - name: "T1"
        days: 1
"""
        config = parse_config(yaml_str)
        assert config.calendar is not None
        assert config.calendar.start_date == date(2026, 3, 9)
        assert config.calendar.show_weekends is False

    def test_calendar_defaults(self):
        """Missing calendar section should produce sensible defaults."""
        yaml_str = """
workers: 1
projects:
  - name: "P1"
    tasks:
      - name: "T1"
        days: 1
"""
        config = parse_config(yaml_str)
        assert config.calendar is not None
        assert config.calendar.start_date == date.today()
        assert config.calendar.show_weekends is True


class TestComputeCalendarDates:
    """Tests for the compute_calendar_dates helper."""

    def test_weekdays_only_skips_weekends(self):
        """Starting Monday, 6 working days should skip Sat+Sun."""
        settings = CalendarSettings(start_date=date(2026, 3, 9), show_weekends=False)
        dates = compute_calendar_dates(settings, total_days=6)
        # Mon 9, Tue 10, Wed 11, Thu 12, Fri 13, Mon 16
        assert len(dates) == 6
        assert dates[0] == date(2026, 3, 9)
        assert dates[4] == date(2026, 3, 13)  # Friday
        assert dates[5] == date(2026, 3, 16)  # Monday (skipped weekend)

    def test_all_days_includes_weekends(self):
        settings = CalendarSettings(start_date=date(2026, 3, 9), show_weekends=True)
        dates = compute_calendar_dates(settings, total_days=7)
        assert len(dates) == 7
        # Consecutive calendar days
        assert dates[6] == date(2026, 3, 15)

    def test_zero_days_returns_empty(self):
        settings = CalendarSettings(start_date=date(2026, 3, 9), show_weekends=True)
        dates = compute_calendar_dates(settings, total_days=0)
        assert dates == []

    def test_start_on_weekend_weekdays_only(self):
        """If start is Saturday and weekdays only, first date should be Monday."""
        settings = CalendarSettings(start_date=date(2026, 3, 14), show_weekends=False)
        dates = compute_calendar_dates(settings, total_days=1)
        assert dates[0] == date(2026, 3, 16)  # Monday
