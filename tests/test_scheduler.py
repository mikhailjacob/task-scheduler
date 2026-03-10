"""Tests for Feature 2: Task Scheduling Algorithm

Tests that tasks are assigned to workers using greedy LPT scheduling,
producing a balanced, non-overlapping schedule.
"""
import pytest
from backend import Task, Config, ScheduledTask, Schedule, schedule_tasks


def make_config(workers, task_specs):
    """Helper: create a Config from (name, days, project) tuples."""
    tasks = [
        Task(name=n, days=d, project=p, task_id=f"{p}/{n}")
        for n, d, p in task_specs
    ]
    return Config(workers=workers, tasks=tasks)


class TestScheduleTasks:
    """Tests for the schedule_tasks function."""

    def test_returns_schedule_object(self):
        config = make_config(2, [("T1", 3, "P1"), ("T2", 2, "P1")])
        result = schedule_tasks(config)
        assert isinstance(result, Schedule)

    def test_all_tasks_assigned(self):
        """Every task in the config must appear exactly once in the schedule."""
        config = make_config(2, [
            ("T1", 3, "P1"), ("T2", 2, "P1"), ("T3", 4, "P2"),
        ])
        result = schedule_tasks(config)
        scheduled_names = {st.task.name for st in result.assignments}
        assert scheduled_names == {"T1", "T2", "T3"}

    def test_no_overlapping_tasks_per_worker(self):
        """Tasks for the same worker must not overlap in time."""
        config = make_config(1, [
            ("T1", 3, "P1"), ("T2", 2, "P1"), ("T3", 4, "P2"),
        ])
        result = schedule_tasks(config)
        # With 1 worker, tasks must be sequential
        assignments = sorted(result.assignments, key=lambda s: s.start_day)
        for i in range(len(assignments) - 1):
            assert assignments[i].end_day <= assignments[i + 1].start_day

    def test_task_duration_matches(self):
        """Scheduled task end_day - start_day must equal task.days."""
        config = make_config(2, [("T1", 5, "P1"), ("T2", 3, "P2")])
        result = schedule_tasks(config)
        for st in result.assignments:
            assert st.end_day - st.start_day == st.task.days

    def test_balanced_distribution(self):
        """Tasks should be reasonably balanced across workers."""
        config = make_config(2, [
            ("T1", 4, "P1"), ("T2", 4, "P1"),
            ("T3", 4, "P2"), ("T4", 4, "P2"),
        ])
        result = schedule_tasks(config)
        worker_loads = {}
        for st in result.assignments:
            worker_loads[st.worker] = worker_loads.get(st.worker, 0) + st.task.days
        loads = list(worker_loads.values())
        assert max(loads) - min(loads) <= 4  # reasonable balance

    def test_total_days_correct(self):
        """total_days should be the makespan (max end_day across all tasks)."""
        config = make_config(2, [("T1", 5, "P1"), ("T2", 3, "P2")])
        result = schedule_tasks(config)
        expected = max(st.end_day for st in result.assignments)
        assert result.total_days == expected

    def test_single_task_single_worker(self):
        """Edge case: one task, one worker."""
        config = make_config(1, [("T1", 3, "P1")])
        result = schedule_tasks(config)
        assert len(result.assignments) == 1
        st = result.assignments[0]
        assert st.worker == 0
        assert st.start_day == 0
        assert st.end_day == 3
