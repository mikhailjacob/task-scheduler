"""YAML configuration parsing and validation.

Handles v1 (simple ``workers: N``), v2 (named workers, calendar,
``parallel: true``), and v3 (indexed tasks, phases, preferred workers,
transitive dependencies) configuration formats.
All new fields are optional for backward compatibility.
"""

from __future__ import annotations

import re
from collections import deque
from datetime import date

import yaml

from .models import CalendarSettings, Config, Task, WorkerInfo

_INDEX_RE = re.compile(r"^(\d+)([A-Za-z]?)$")


class ConfigParser:
    """Parses and validates YAML configuration into Config objects.

    The parser enforces:
      - At least one worker (named or anonymous)
      - At least one project with at least one task
      - Positive integer durations for all tasks
      - Valid dependency references (existing task IDs or phase IDs)
      - Acyclic dependency graph (no circular dependencies)
      - Transitive dependency closure
    """

    @staticmethod
    def parse(yaml_string: str) -> Config:
        """Parse a YAML string into a Config object."""
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

        if workers_count > 1000:
            raise ValueError(
                f"Worker count ({workers_count}) exceeds maximum of 1000"
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
        # phase_id -> list of task_ids in that phase
        phase_tasks: dict[str, list[str]] = {}

        for proj in projects:
            proj_name = proj.get("name")
            if not proj_name:
                raise ValueError("Each project must have a 'name'")

            phases_raw = proj.get("phases")
            tasks_raw = proj.get("tasks")

            if phases_raw and isinstance(phases_raw, list):
                # v3 phase-based project
                for phase in phases_raw:
                    phase_name = phase.get("name")
                    if not phase_name:
                        raise ValueError(
                            f"Each phase in '{proj_name}' must have a 'name'"
                        )
                    phase_id = f"{proj_name}/{phase_name}"
                    phase_task_list = phase.get("tasks")
                    if not phase_task_list or not isinstance(phase_task_list, list):
                        raise ValueError(
                            f"Phase '{phase_name}' in '{proj_name}' must "
                            "have a non-empty 'tasks' list"
                        )
                    phase_tasks[phase_id] = []
                    parsed = ConfigParser._parse_task_list(
                        phase_task_list, proj_name, phase_name,
                    )
                    for task in parsed:
                        tasks.append(task)
                        all_task_ids.add(task.task_id)
                        phase_tasks[phase_id].append(task.task_id)

            elif tasks_raw and isinstance(tasks_raw, list):
                # flat task list (v1/v2/v3 without phases)
                parsed = ConfigParser._parse_task_list(
                    tasks_raw, proj_name, None,
                )
                for task in parsed:
                    tasks.append(task)
                    all_task_ids.add(task.task_id)
            else:
                raise ValueError(
                    f"Project '{proj_name}' must have 'tasks' or 'phases'"
                )

        # --- Resolve phase-level dependencies ---
        for t in tasks:
            expanded_deps: list[str] = []
            for dep in t.depends_on:
                if dep in phase_tasks:
                    # Phase-level dep: expand to all tasks in phase
                    for ptid in phase_tasks[dep]:
                        if ptid not in expanded_deps:
                            expanded_deps.append(ptid)
                else:
                    if dep not in expanded_deps:
                        expanded_deps.append(dep)
            t.depends_on = expanded_deps

        if len(tasks) > 10_000:
            raise ValueError(
                f"Task count ({len(tasks)}) exceeds maximum of 10,000"
            )

        # --- Validate preferred workers ---
        known_worker_names = {wi.name for wi in worker_names}
        for t in tasks:
            for pw in t.preferred_workers:
                if pw not in known_worker_names:
                    raise ValueError(
                        f"Task '{t.task_id}' has unknown preferred "
                        f"worker '{pw}'"
                    )

        # --- Validate dependency references ---
        for t in tasks:
            for dep in t.depends_on:
                if dep not in all_task_ids:
                    raise ValueError(
                        f"Task '{t.task_id}' has invalid dependency "
                        f"'{dep}': not found"
                    )

        ConfigParser._detect_circular(tasks)

        # --- Compute transitive closure ---
        ConfigParser._transitive_close(tasks)

        return Config(
            workers=workers_count,
            tasks=tasks,
            worker_names=worker_names,
            calendar=calendar,
        )

    @staticmethod
    def _parse_task_list(
        task_list: list,
        proj_name: str,
        phase_name: str | None,
    ) -> list[Task]:
        """Parse a list of task dicts into Task objects.

        Supports v1/v2 (sequential-by-default, parallel: true) and
        v3 (index-based parallelism).  Detects the format by checking
        whether any task has an ``index`` field.
        """
        has_index = any(
            isinstance(t, dict) and "index" in t for t in task_list
        )

        if has_index:
            return ConfigParser._parse_indexed_tasks(
                task_list, proj_name, phase_name,
            )
        return ConfigParser._parse_sequential_tasks(
            task_list, proj_name, phase_name,
        )

    @staticmethod
    def _parse_sequential_tasks(
        task_list: list,
        proj_name: str,
        phase_name: str | None,
    ) -> list[Task]:
        """Parse v1/v2 sequential-by-default task list."""
        tasks: list[Task] = []
        prev_task_id: str | None = None
        prev_deps: list[str] = []

        for t in task_list:
            task_name = t.get("name") if isinstance(t, dict) else None
            if not task_name:
                ctx = phase_name or proj_name
                raise ValueError(f"Each task in '{ctx}' must have a 'name'")
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

            if phase_name:
                task_id = f"{proj_name}/{phase_name}/{task_name}"
            else:
                task_id = f"{proj_name}/{task_name}"

            is_parallel = bool(t.get("parallel", False))
            explicit_deps = list(t.get("depends_on", []))
            preferred = list(t.get("preferred_workers", []))

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
                preferred_workers=preferred,
            )
            tasks.append(task)
            prev_task_id = task_id
            prev_deps = deps

        return tasks

    @staticmethod
    def _parse_indexed_tasks(
        task_list: list,
        proj_name: str,
        phase_name: str | None,
    ) -> list[Task]:
        """Parse v3 index-based task list.

        Tasks with the same numeric prefix but different letter suffixes
        are parallel.  Index N implicitly depends on all tasks at index N-1.
        """
        tasks: list[Task] = []
        # index_str -> list of task_ids at that index
        index_groups: dict[int, list[str]] = {}

        for t in task_list:
            if not isinstance(t, dict):
                raise ValueError("Each task must be a mapping")
            task_name = t.get("name")
            if not task_name:
                ctx = phase_name or proj_name
                raise ValueError(f"Each task in '{ctx}' must have a 'name'")
            days = t.get("days")
            if days is None:
                raise ValueError(
                    f"Task '{task_name}' in '{proj_name}' is missing 'days'"
                )
            if not isinstance(days, int) or days < 1:
                raise ValueError(
                    f"Task '{task_name}' has invalid 'days': "
                    "must be a positive integer"
                )

            raw_index = t.get("index")
            if raw_index is None:
                raise ValueError(
                    f"Task '{task_name}' in '{proj_name}' is missing 'index'"
                )
            idx_str = str(raw_index)
            m = _INDEX_RE.match(idx_str)
            if not m:
                raise ValueError(
                    f"Task '{task_name}' has invalid index '{idx_str}': "
                    "must be a number or number+letter (e.g. 1, 2, 1A, 1B)"
                )
            num_part = int(m.group(1))

            if phase_name:
                task_id = f"{proj_name}/{phase_name}/{task_name}"
            else:
                task_id = f"{proj_name}/{task_name}"

            explicit_deps = list(t.get("depends_on", []))
            preferred = list(t.get("preferred_workers", []))

            # Build implicit deps: depend on all tasks at prev index number
            deps: list[str] = []
            prev_num = num_part - 1
            if prev_num in index_groups:
                for prev_tid in index_groups[prev_num]:
                    if prev_tid not in deps:
                        deps.append(prev_tid)

            for ed in explicit_deps:
                if ed not in deps:
                    deps.append(ed)

            task = Task(
                name=task_name, days=days, project=proj_name,
                task_id=task_id, depends_on=deps,
                index=idx_str,
                preferred_workers=preferred,
            )
            tasks.append(task)
            index_groups.setdefault(num_part, []).append(task_id)

        return tasks

    @staticmethod
    def _transitive_close(tasks: list[Task]) -> None:
        """Compute transitive closure of dependencies in-place.

        After this, each task's ``depends_on`` includes all direct and
        indirect dependencies.
        """
        dep_map: dict[str, set[str]] = {
            t.task_id: set(t.depends_on) for t in tasks
        }

        # Topological order for correct propagation
        in_degree: dict[str, int] = {tid: 0 for tid in dep_map}
        children: dict[str, list[str]] = {tid: [] for tid in dep_map}
        for tid, deps in dep_map.items():
            for d in deps:
                children[d].append(tid)
                in_degree[tid] += 1

        queue = deque(tid for tid, deg in in_degree.items() if deg == 0)
        topo: list[str] = []
        while queue:
            node = queue.popleft()
            topo.append(node)
            for child in children[node]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        # Propagate: each node inherits all deps of its deps
        all_deps: dict[str, set[str]] = {}
        for tid in topo:
            full = set(dep_map[tid])
            for d in dep_map[tid]:
                if d in all_deps:
                    full |= all_deps[d]
            all_deps[tid] = full

        task_by_id = {t.task_id: t for t in tasks}
        for tid, full in all_deps.items():
            task_by_id[tid].depends_on = sorted(full)

    @staticmethod
    def _detect_circular(tasks: list[Task]) -> None:
        """Raise ValueError if the dependency graph contains a cycle.

        Uses Kahn's algorithm: performs a BFS-based topological sort
        and checks whether all nodes were visited.  If not, the
        unvisited nodes form one or more cycles.
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
