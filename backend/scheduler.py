"""Dependency-aware task scheduling algorithm.

Implements a topological-sort-based scheduler (Kahn's algorithm)
with Longest Processing Time (LPT) tiebreaking.  Respects task
dependencies and per-worker availability offsets.

Complexity: O(n log n + n*k) where n = tasks, k = workers.
"""

from __future__ import annotations

import heapq

from .models import Config, Schedule, ScheduledTask, WorkerInfo


class TaskScheduler:
    """Assigns tasks to workers respecting dependencies and availability.

    Uses topological sort (Kahn's algorithm) with LPT tiebreaking.
    """

    @staticmethod
    def schedule(config: Config) -> Schedule:
        """Assign tasks to workers respecting dependencies and availability.

        Algorithm:
            1. Topologically sort tasks by dependencies.
            2. For each task, find the earliest start time per worker =
               max(worker_current_end, all dependency end times,
               worker availability offset).
            3. Assign the task to the worker that yields the earliest finish.
        """
        tasks = config.tasks
        n_workers = config.workers
        worker_infos = config.worker_names or [
            WorkerInfo(name=f"Worker {i+1}", available_in=0)
            for i in range(n_workers)
        ]

        # Build adjacency and in-degree for topological sort
        task_map = {t.task_id: t for t in tasks}
        in_degree: dict[str, int] = {t.task_id: 0 for t in tasks}
        children: dict[str, list[str]] = {t.task_id: [] for t in tasks}
        for t in tasks:
            for dep in t.depends_on:
                children[dep].append(t.task_id)
                in_degree[t.task_id] += 1

        # Topological sort (Kahn's) — break ties by longest task first (LPT)
        ready = [
            (-t.days, t.task_id)
            for t in tasks
            if in_degree[t.task_id] == 0
        ]
        heapq.heapify(ready)

        topo_order: list[str] = []
        while ready:
            _, tid = heapq.heappop(ready)
            topo_order.append(tid)
            for child in children[tid]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    heapq.heappush(
                        ready, (-task_map[child].days, child)
                    )

        # Worker current-end tracker
        worker_end: list[int] = [w.available_in for w in worker_infos]
        scheduled_end: dict[str, int] = {}

        assignments: list[ScheduledTask] = []
        for tid in topo_order:
            task = task_map[tid]

            # Earliest possible start from dependencies
            dep_end = max(
                (scheduled_end[d] for d in task.depends_on), default=0
            )

            # Pick worker whose max(current_end, dep_end) is minimised
            best_worker = -1
            best_start = float("inf")
            for w in range(n_workers):
                candidate_start = max(worker_end[w], dep_end)
                if candidate_start < best_start:
                    best_start = candidate_start
                    best_worker = w

            start = int(best_start)
            end = start + task.days
            assignments.append(ScheduledTask(
                task=task, worker=best_worker,
                start_day=start, end_day=end,
            ))
            worker_end[best_worker] = end
            scheduled_end[tid] = end

        total_days = (
            max(st.end_day for st in assignments) if assignments else 0
        )
        return Schedule(
            assignments=assignments,
            total_days=total_days,
            worker_names=worker_infos,
        )


# Convenience alias for backward-compatible imports.
schedule_tasks = TaskScheduler.schedule
