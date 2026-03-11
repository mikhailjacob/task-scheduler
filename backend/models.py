"""Data models for the Work Scheduler application.

All domain objects are defined as Python dataclasses for clarity and
immutability intent.  These models flow through the system:

    YAML string  --(parser)-->  Config  --(scheduler)-->  Schedule
                                                        --(colors)-->  color map
                                                        --(calendar)--> date list
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Task:
    """A single schedulable unit of work.

    Attributes:
        name: Human-readable task name.
        days: Duration of the task in working days (must be >= 1).
        project: Name of the parent project this task belongs to.
        task_id: Unique identifier in ``"Project/Task"`` or
            ``"Project/Phase/Task"`` format.
        depends_on: List of ``task_id`` strings that must complete
            before this task can start.
        index: Alphanumeric index (e.g. ``"1"``, ``"2"``, ``"1A"``).
            Tasks sharing the same numeric prefix but different letter
            suffixes are parallel siblings.
        preferred_workers: Worker names that prefer this task. The
            scheduler will try to assign the task to a preferred
            worker when possible.
    """
    name: str
    days: int
    project: str
    task_id: str = ""
    depends_on: list[str] = field(default_factory=list)
    index: str = ""
    preferred_workers: list[str] = field(default_factory=list)


@dataclass
class WorkerInfo:
    """A named worker with an optional availability offset.

    Attributes:
        name: Display name shown in the Gantt chart worker label.
        available_in: Number of working days from the schedule start
            before this worker becomes available.  Renders as a
            hatched "Current Tasks" block in the UI.
    """
    name: str
    available_in: int = 0


@dataclass
class CalendarSettings:
    """Calendar display configuration.

    Attributes:
        start_date: The real-world date corresponding to day 0 of the
            schedule.  Defaults to today.
        show_weekends: When ``False``, Saturdays and Sundays are skipped
            in the calendar mapping so that 5 working days = Mon–Fri.
    """
    start_date: date = field(default_factory=date.today)
    show_weekends: bool = True


@dataclass
class Config:
    """Parsed configuration: worker count, tasks, and optional extras.

    Attributes:
        workers: Total number of workers available.
        tasks: Flat list of all tasks across all projects, with
            dependency information already resolved.
        worker_names: Per-worker metadata (name and availability).
            If the config used anonymous ``workers: N``, this is
            auto-populated with ``Worker 1`` through ``Worker N``.
        calendar: Calendar display settings, or ``None`` to use defaults.
    """
    workers: int
    tasks: list[Task]
    worker_names: list[WorkerInfo] = field(default_factory=list)
    calendar: CalendarSettings | None = None


@dataclass
class ScheduledTask:
    """A task assigned to a specific worker with start/end days.

    Attributes:
        task: The original Task being scheduled.
        worker: Zero-indexed worker ID.
        start_day: Inclusive start day (0-indexed).
        end_day: Exclusive end day.  Duration = ``end_day - start_day``.
    """
    task: Task
    worker: int
    start_day: int
    end_day: int


@dataclass
class Schedule:
    """Complete schedule: list of assignments and total makespan.

    Attributes:
        assignments: All scheduled tasks with worker and timing info.
        total_days: The makespan — ``max(end_day)`` across all
            assignments.  Determines the width of the Gantt chart.
        worker_names: Per-worker metadata passed through from Config
            for template rendering.
    """
    assignments: list[ScheduledTask]
    total_days: int
    worker_names: list[WorkerInfo] = field(default_factory=list)
