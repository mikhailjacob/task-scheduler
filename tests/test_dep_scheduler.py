"""Tests for Feature 9: Dependency-Aware Scheduling

Tests that the scheduler respects dependency ordering, worker availability
offsets, and still balances load when possible.
"""
import pytest
from backend import (
    Task, Config, WorkerInfo, ScheduledTask, Schedule, schedule_tasks,
)


def _make_task(name, days, project, depends_on=None):
    return Task(
        name=name, days=days, project=project,
        task_id=f"{project}/{name}",
        depends_on=depends_on or [],
    )


def _find(schedule, task_name):
    return next(st for st in schedule.assignments if st.task.name == task_name)


class TestDependencyScheduling:
    """Tests that dependency constraints are honoured."""

    def test_dependent_task_starts_after_predecessor(self):
        tasks = [
            _make_task("A", 3, "P1"),
            _make_task("B", 2, "P1", depends_on=["P1/A"]),
        ]
        config = Config(workers=2, tasks=tasks)
        sched = schedule_tasks(config)
        a = _find(sched, "A")
        b = _find(sched, "B")
        assert b.start_day >= a.end_day

    def test_parallel_tasks_can_overlap(self):
        """Two independent tasks on different workers can run simultaneously."""
        tasks = [
            _make_task("A", 3, "P1"),
            _make_task("B", 3, "P2"),
        ]
        config = Config(workers=2, tasks=tasks)
        sched = schedule_tasks(config)
        a = _find(sched, "A")
        b = _find(sched, "B")
        # With 2 workers and no deps, both should start at 0
        assert a.start_day == 0
        assert b.start_day == 0

    def test_cross_project_dependency(self):
        tasks = [
            _make_task("API", 5, "Backend"),
            _make_task("UI", 3, "Frontend", depends_on=["Backend/API"]),
        ]
        config = Config(workers=2, tasks=tasks)
        sched = schedule_tasks(config)
        api = _find(sched, "API")
        ui = _find(sched, "UI")
        assert ui.start_day >= api.end_day

    def test_diamond_dependency(self):
        """A -> B, A -> C, B+C -> D. D must start after both B and C."""
        tasks = [
            _make_task("A", 2, "P"),
            _make_task("B", 3, "P", depends_on=["P/A"]),
            _make_task("C", 1, "P", depends_on=["P/A"]),
            _make_task("D", 2, "P", depends_on=["P/B", "P/C"]),
        ]
        config = Config(workers=3, tasks=tasks)
        sched = schedule_tasks(config)
        b = _find(sched, "B")
        c = _find(sched, "C")
        d = _find(sched, "D")
        assert d.start_day >= b.end_day
        assert d.start_day >= c.end_day

    def test_no_deps_falls_back_to_balanced(self):
        """With no dependencies the scheduler should still balance load."""
        tasks = [
            _make_task("T1", 4, "P"),
            _make_task("T2", 4, "P"),
        ]
        # Remove default sequential dep for this test
        for t in tasks:
            t.depends_on = []
        config = Config(workers=2, tasks=tasks)
        sched = schedule_tasks(config)
        workers_used = {st.worker for st in sched.assignments}
        assert len(workers_used) == 2  # both workers should be used


class TestWorkerAvailability:
    """Tests for worker availability offsets in scheduling."""

    def test_worker_offset_delays_start(self):
        tasks = [_make_task("A", 3, "P")]
        workers = [WorkerInfo(name="Alice", available_in=5)]
        config = Config(workers=1, tasks=tasks, worker_names=workers)
        sched = schedule_tasks(config)
        a = _find(sched, "A")
        assert a.start_day >= 5

    def test_offset_and_dependency_max(self):
        """start = max(dependency_end, worker_availability)."""
        tasks = [
            _make_task("A", 3, "P"),
            _make_task("B", 2, "P", depends_on=["P/A"]),
        ]
        # Worker 0 available at 0, Worker 1 available at 10
        workers = [
            WorkerInfo(name="Fast", available_in=0),
            WorkerInfo(name="Late", available_in=10),
        ]
        config = Config(workers=2, tasks=tasks, worker_names=workers)
        sched = schedule_tasks(config)
        b = _find(sched, "B")
        a = _find(sched, "A")
        # B depends on A (ends at 3) and if assigned to Late, start >= 10
        assert b.start_day >= a.end_day

    def test_current_tasks_block_data(self):
        """Schedule should include availability offset metadata."""
        tasks = [_make_task("A", 3, "P")]
        workers = [WorkerInfo(name="Bob", available_in=5)]
        config = Config(workers=1, tasks=tasks, worker_names=workers)
        sched = schedule_tasks(config)
        assert sched.worker_names[0].name == "Bob"
        assert sched.worker_names[0].available_in == 5
