"""Tests for Feature 16: Preferred Worker Allocation."""

import pytest

from backend.parser import parse_config
from backend.scheduler import TaskScheduler


# ---------------------------------------------------------------------------
# Preferred workers parsed correctly
# ---------------------------------------------------------------------------

class TestPreferredWorkerParsing:
    """preferred_workers field is parsed on tasks."""

    CFG = """\
worker_names:
  - name: Alice
  - name: Bob
projects:
  - name: P
    tasks:
      - name: Task1
        days: 2
        index: 1
        preferred_workers:
          - Alice
      - name: Task2
        days: 3
        index: 1
"""

    def test_preferred_workers_stored(self):
        cfg = parse_config(self.CFG)
        by_name = {t.name: t for t in cfg.tasks}
        assert by_name["Task1"].preferred_workers == ["Alice"]

    def test_empty_preferred_defaults_to_empty(self):
        cfg = parse_config(self.CFG)
        by_name = {t.name: t for t in cfg.tasks}
        assert by_name["Task2"].preferred_workers == []


# ---------------------------------------------------------------------------
# Preferred worker selection when tied
# ---------------------------------------------------------------------------

class TestPreferredWorkerScheduling:
    """Scheduler prefers a preferred worker among equally-timed options."""

    def test_preferred_worker_chosen_when_tied(self):
        """When both workers can start at day 0, prefer the named one."""
        yaml_str = """\
worker_names:
  - name: Alice
  - name: Bob
projects:
  - name: P
    tasks:
      - name: OnlyTask
        days: 3
        index: 1
        preferred_workers:
          - Bob
"""
        cfg = parse_config(yaml_str)
        sched = TaskScheduler.schedule(cfg)
        assert len(sched.assignments) == 1
        # Bob is worker index 1
        assert sched.assignments[0].worker == 1

    def test_preference_does_not_sacrifice_start_time(self):
        """A non-preferred worker that can start earlier wins."""
        yaml_str = """\
worker_names:
  - name: Alice
  - name: Bob
projects:
  - name: P
    tasks:
      - name: Blocker
        days: 5
        index: 1
        preferred_workers:
          - Bob
      - name: Target
        days: 2
        index: 1
        preferred_workers:
          - Bob
"""
        cfg = parse_config(yaml_str)
        sched = TaskScheduler.schedule(cfg)
        by_name = {st.task.name: st for st in sched.assignments}
        # Both tasks at index 1 are parallel; Blocker goes to Bob (pref+tied)
        # Target should go to Alice at day 0 (not wait for Bob to finish)
        assert by_name["Target"].start_day == 0

    def test_fallback_when_preferred_worker_busy(self):
        """If preferred worker cannot match best start, fall back."""
        yaml_str = """\
worker_names:
  - name: Alice
  - name: Bob
projects:
  - name: P
    tasks:
      - name: First
        days: 3
        index: 1
        preferred_workers:
          - Bob
      - name: Second
        days: 2
        index: 2
        preferred_workers:
          - Bob
"""
        cfg = parse_config(yaml_str)
        sched = TaskScheduler.schedule(cfg)
        by_name = {st.task.name: st for st in sched.assignments}
        # First goes to Bob (preferred, tied at day 0)
        assert by_name["First"].worker == 1
        # Second depends on First (index 2 > 1), both workers tied at day 3
        # Bob is preferred and tied, so Bob gets it
        assert by_name["Second"].worker == 1

    def test_multiple_preferred_workers(self):
        """Task with multiple preferred workers picks first tied preferred."""
        yaml_str = """\
worker_names:
  - name: Alice
  - name: Bob
  - name: Carol
projects:
  - name: P
    tasks:
      - name: T
        days: 1
        index: 1
        preferred_workers:
          - Bob
          - Carol
"""
        cfg = parse_config(yaml_str)
        sched = TaskScheduler.schedule(cfg)
        # All 3 workers free — Bob or Carol preferred. Bob appears first.
        assert sched.assignments[0].worker in (1, 2)


# ---------------------------------------------------------------------------
# Preferred workers with availability offsets
# ---------------------------------------------------------------------------

class TestPreferredWithAvailability:
    """Preferred workers interact correctly with available_in offsets."""

    def test_available_later_preferred_not_chosen(self):
        """Preferred worker available later loses to earlier worker."""
        yaml_str = """\
worker_names:
  - name: Alice
  - name: Bob
    available_in: 5
projects:
  - name: P
    tasks:
      - name: T
        days: 2
        index: 1
        preferred_workers:
          - Bob
"""
        cfg = parse_config(yaml_str)
        sched = TaskScheduler.schedule(cfg)
        # Alice starts day 0, Bob day 5. Alice is earlier => Alice chosen.
        assert sched.assignments[0].worker == 0
        assert sched.assignments[0].start_day == 0

    def test_available_same_time_preferred_wins(self):
        """Preferred worker at same availability is chosen."""
        yaml_str = """\
worker_names:
  - name: Alice
    available_in: 3
  - name: Bob
    available_in: 3
projects:
  - name: P
    tasks:
      - name: T
        days: 2
        index: 1
        preferred_workers:
          - Bob
"""
        cfg = parse_config(yaml_str)
        sched = TaskScheduler.schedule(cfg)
        assert sched.assignments[0].worker == 1
        assert sched.assignments[0].start_day == 3
