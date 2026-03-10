"""YAML configuration parsing and validation.

Handles both v1 (simple ``workers: N``) and v2 (named workers,
calendar settings, task dependencies) configuration formats.
All new fields are optional for backward compatibility.
"""

from __future__ import annotations

from collections import deque
from datetime import date

import yaml

from .models import CalendarSettings, Config, Task, WorkerInfo


class ConfigParser:
    """Parses and validates YAML configuration into Config objects.

    The parser enforces:
      - At least one worker (named or anonymous)
      - At least one project with at least one task
      - Positive integer durations for all tasks
      - Valid dependency references (existing task IDs)
      - Acyclic dependency graph (no circular dependencies)
    """

    @staticmethod
    def parse(yaml_string: str) -> Config:
        """Parse a YAML string into a Config object.

        Supports both v1 (simple) and v2 (dependencies, named workers,
        calendar) config formats.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        data = yaml.safe_load(yaml_string)
        if not isinstance(data, dict):
            raise ValueError("Invalid YAML: expected a mapping at the top level")

        # --- Workers (named or anonymous) ---
        worker_names_raw = data.get("worker_names")
        workers_count = data.get("workers")

        worker_names: list[WorkerInfo] = []
        if worker_names_raw and isinstance(worker_names_raw, list):
            for w in worker_names_raw:
                wname = w.get("name") if isinstance(w, dict) else w
                if not wname:
                    raise ValueError("Each worker must have a 'name'")
                avail = w.get("available_in", 0) if isinstance(w, dict) else 0
                if not isinstance(avail, int) or avail < 0:
                    raise ValueError(
                        f"Worker '{wname}' has invalid 'available_in': "
                        "must be a non-negative integer"
                    )
                worker_names.append(WorkerInfo(name=wname, available_in=avail))
            workers_count = len(worker_names)
        elif workers_count is not None:
            if not isinstance(workers_count, int) or workers_count < 1:
                raise ValueError("'workers' must be a positive integer")
            worker_names = [
                WorkerInfo(name=f"Worker {i+1}", available_in=0)
                for i in range(workers_count)
            ]
        else:
            raise ValueError(
                "Missing required field: 'workers' or 'worker_names'"
            )

        # --- Calendar settings ---
        cal_raw = data.get("calendar")
        if cal_raw and isinstance(cal_raw, dict):
            sd = cal_raw.get("start_date")
            if sd:
                if isinstance(sd, date):
                    start_date = sd
                else:
                    start_date = date.fromisoformat(str(sd))
            else:
                start_date = date.today()
            show_weekends = cal_raw.get("show_weekends", True)
            calendar = CalendarSettings(
                start_date=start_date, show_weekends=show_weekends
            )
        else:
            calendar = CalendarSettings()

        # --- Projects and tasks ---
        projects = data.get("projects")
        if not projects or not isinstance(projects, list):
            raise ValueError("Missing or empty required field: 'projects'")

        tasks: list[Task] = []
        all_task_ids: set[str] = set()

        for proj in projects:
            proj_name = proj.get("name")
            if not proj_name:
                raise ValueError("Each project must have a 'name'")
            proj_tasks = proj.get("tasks")
            if not proj_tasks or not isinstance(proj_tasks, list):
                raise ValueError(
                    f"Project '{proj_name}' must have a non-empty 'tasks' list"
                )

            prev_task_id: str | None = None
            prev_deps: list[str] = []

            for t in proj_tasks:
                task_name = t.get("name") if isinstance(t, dict) else None
                if not task_name:
                    raise ValueError(
                        f"Each task in '{proj_name}' must have a 'name'"
                    )
                days = t.get("days") if isinstance(t, dict) else None
                if days is None:
                    raise ValueError(
                        f"Task '{task_name}' in '{proj_name}' is missing 'days'"
                    )
                if not isinstance(days, int) or days < 1:
                    raise ValueError(
                        f"Task '{task_name}' has invalid 'days': "
                        "must be a positive integer"
                    )

                task_id = f"{proj_name}/{task_name}"
                is_parallel = bool(t.get("parallel", False))
                explicit_deps = list(t.get("depends_on", []))

                deps: list[str] = []
                if is_parallel:
                    deps.extend(prev_deps)
                else:
                    if prev_task_id is not None:
                        deps.append(prev_task_id)

                for ed in explicit_deps:
                    if ed not in deps:
                        deps.append(ed)

                task = Task(
                    name=task_name, days=days, project=proj_name,
                    task_id=task_id, depends_on=deps,
                )
                tasks.append(task)
                all_task_ids.add(task_id)

                prev_task_id = task_id
                prev_deps = deps

        # Validate dependency references
        for t in tasks:
            for dep in t.depends_on:
                if dep not in all_task_ids:
                    raise ValueError(
                        f"Task '{t.task_id}' has invalid dependency "
                        f"'{dep}': not found"
                    )

        ConfigParser._detect_circular(tasks)

        return Config(
            workers=workers_count,
            tasks=tasks,
            worker_names=worker_names,
            calendar=calendar,
        )

    @staticmethod
    def _detect_circular(tasks: list[Task]) -> None:
        """Raise ValueError if the dependency graph contains a cycle.

        Uses Kahn's algorithm: performs a BFS-based topological sort
        and checks whether all nodes were visited.  If not, the
        unvisited nodes form one or more cycles.

        Args:
            tasks: All parsed tasks with ``depends_on`` already set.

        Raises:
            ValueError: If a cycle is detected.
        """
        in_degree: dict[str, int] = {t.task_id: 0 for t in tasks}
        adj: dict[str, list[str]] = {t.task_id: [] for t in tasks}
        for t in tasks:
            for dep in t.depends_on:
                adj[dep].append(t.task_id)
                in_degree[t.task_id] += 1

        queue = deque(tid for tid, deg in in_degree.items() if deg == 0)
        visited = 0
        while queue:
            node = queue.popleft()
            visited += 1
            for child in adj[node]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        if visited != len(tasks):
            raise ValueError("Circular dependency detected in task graph")


# Convenience alias for backward-compatible imports.
parse_config = ConfigParser.parse
