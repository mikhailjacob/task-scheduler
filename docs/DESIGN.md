# Work Scheduler - Design Document

## Overview

A locally-hosted web application that lets users define task schedules either
by uploading a YAML configuration file or by building one interactively in a
graphical editor. The backend parses the configuration, schedules tasks across
workers respecting dependencies and availability constraints, and displays the
result as an interactive Gantt chart.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Browser (Frontend)                     │
│  ┌───────────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │ File Upload   │  │ Config      │  │ Gantt Chart    │  │
│  │ Form          │  │ Editor      │  │ (HTML/CSS)     │  │
│  │               │  │ (HTML/JS)   │  │ - Swimlanes    │  │
│  │               │  │             │  │ - Tooltips     │  │
│  └───────────────┘  └─────────────┘  └────────────────┘  │
└──────────────────────┬───────────────────────────────────┘
                       │ HTTP
┌──────────────────────┴───────────────────────────────────┐
│                 Flask Backend (Python)                    │
│  ┌────────────────┐  ┌────────────────────────────────┐  │
│  │ YAML Parser    │  │ Task Scheduler                 │  │
│  │ - Validation   │  │ - Topological sort             │  │
│  │ - Dependencies │  │ - LPT balancing                │  │
│  └────────────────┘  └────────────────────────────────┘  │
│  ┌────────────────┐  ┌────────────────────────────────┐  │
│  │ Color Assigner │  │ Editor Service                 │  │
│  │ - Per-project  │  │ - JSON ↔ YAML conversion       │  │
│  └────────────────┘  └────────────────────────────────┘  │
│  ┌────────────────┐                                      │
│  │ Calendar       │  Jinja2 server-side rendering        │
│  │ - Date mapping │                                      │
│  └────────────────┘                                      │
└──────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer    | Technology       | Rationale                          |
|----------|------------------|------------------------------------|
| Backend  | Python + Flask   | Lightweight, easy to host locally  |
| Config   | PyYAML           | Native YAML parsing                |
| Frontend | HTML + CSS + JS  | No build step, zero dependencies   |
| Testing  | pytest           | Standard Python testing framework  |

## YAML Configuration Format

```yaml
workers: 3

projects:
  - name: "Backend API"
    tasks:
      - name: "Setup database schema"
        days: 3
      - name: "Implement auth endpoints"
        days: 5
  - name: "Frontend"
    tasks:
      - name: "Design mockups"
        days: 2
      - name: "Implement dashboard"
        days: 4
```

## YAML Configuration Format (v2 — with dependencies, named workers, calendar)

Design principles:
- **Sequential by default:** Tasks listed consecutively within a project are
  assumed to depend on their predecessor (i.e. sequential). This minimises
  config verbosity — most real projects have a natural ordering.
- **Opt-in parallelism:** Add `parallel: true` on a task to indicate it can
  run in parallel with the previous task in the same project (it shares the
  same dependency set as its predecessor rather than depending on it).
- **Cross-project dependencies:** Use `depends_on: ["Project/Task"]` to add
  an explicit dependency on a task from any project.
- **All new fields are optional** — old configs remain valid.

```yaml
# Optional: provide worker names and availability offsets
# If omitted, falls back to "workers: N" anonymous workers.
worker_names:
  - name: "Alice"
    available_in: 0      # available immediately (default)
  - name: "Bob"
    available_in: 5      # busy for 5 days with current tasks
  - name: "Charlie"      # available_in defaults to 0

# Legacy anonymous form still supported:
# workers: 3

# Optional calendar settings
calendar:
  start_date: "2026-03-09"   # defaults to today
  show_weekends: false        # false = weekdays only (default: true)

projects:
  - name: "Backend API"
    tasks:
      # These are sequential by default:
      - name: "Setup database schema"
        days: 3
      - name: "Implement auth endpoints"   # implicitly depends on "Setup database schema"
        days: 5
      - name: "Write API documentation"
        parallel: true                      # can run in parallel with "Implement auth endpoints"
        days: 2

  - name: "Frontend"
    tasks:
      - name: "Design mockups"
        days: 2
      - name: "Implement dashboard"        # depends on "Design mockups"
        days: 4
        depends_on:
          - "Backend API/Implement auth endpoints"   # also waits on backend
      - name: "Build login page"
        parallel: true                      # parallel with dashboard
        depends_on:
          - "Backend API/Implement auth endpoints"
        days: 3
```

### Dependency Resolution Rules

1. **Intra-project sequential (default):** Task N depends on Task N-1 within
   the same project, unless Task N has `parallel: true`.
2. **Intra-project parallel:** If `parallel: true`, the task inherits the same
   dependencies as its immediate predecessor (i.e. it has no dependency *on*
   the predecessor, but shares the predecessor's parent).
3. **Cross-project explicit:** `depends_on` lists references in the format
   `"ProjectName/TaskName"`. These are *additive* — they combine with implicit
   intra-project dependencies.
4. **Scheduling constraint:** A task's earliest start =
   `max(all dependency end times, worker availability offset)`.


## Features

### Feature 1: YAML Configuration Parsing
**Description:** Parse and validate a YAML configuration file into internal data models.

**Acceptance Criteria:**
- Parse `workers` count (positive integer)
- Parse `projects` list, each with `name` (string) and `tasks` list
- Each task has `name` (string) and `days` (positive integer)
- Raise clear errors for missing/invalid fields

**Data Models:**
```python
@dataclass
class Task:
    name: str
    days: int
    project: str

@dataclass
class Config:
    workers: int
    tasks: list[Task]  # flattened, with project name attached
```

### Feature 2: Task Scheduling Algorithm
**Description:** Assign tasks to workers using a greedy load-balancing algorithm.

**Algorithm:** Greedy "Longest Processing Time First" (LPT):
1. Sort all tasks by duration descending
2. Maintain a priority queue of workers by current total load
3. Assign each task to the worker with the least current load

**Acceptance Criteria:**
- Each task assigned to exactly one worker
- Tasks for each worker are sequential (no overlap)
- Schedule is reasonably balanced (no worker has >1 task-duration more than optimal)

**Output Model:**
```python
@dataclass
class ScheduledTask:
    task: Task
    worker: int       # 0-indexed worker ID
    start_day: int    # 0-indexed start day
    end_day: int      # exclusive end day

@dataclass
class Schedule:
    assignments: list[ScheduledTask]
    total_days: int
```

### Feature 3: Flask Web Server
**Description:** Minimal Flask application serving the upload page and schedule visualization.

**Routes:**
| Route         | Method | Description                         |
|---------------|--------|-------------------------------------|
| `/`           | GET    | Landing page (upload + editor link) |
| `/upload`     | POST   | Accept YAML, return schedule page   |

**Acceptance Criteria:**
- Server starts on `localhost:5000`
- GET `/` returns HTML with file upload form and link to editor
- POST `/upload` accepts file, parses, schedules, renders chart

### Feature 4: Gantt Chart Visualization
**Description:** Render the schedule as a Gantt chart with workers on Y-axis and time (days) on X-axis.

**Implementation:** Pure HTML/CSS grid rendered server-side via Jinja2 template.

**Acceptance Criteria:**
- Each worker is a row (swimlane)
- Each task is a colored block spanning its duration
- X-axis shows day numbers
- Chart is scrollable for large schedules

### Feature 5: Hover Tooltip Details
**Description:** Hovering over a task block reveals task name, project, and duration.

**Implementation:** CSS tooltips (no JavaScript library needed).

**Acceptance Criteria:**
- Tooltip shows: Task name, Project name, Duration (days), Start day, End day
- Tooltip appears on hover, disappears on mouse leave

### Feature 6: File Upload Endpoint
**Description:** Secure file upload handling on the backend.

**Acceptance Criteria:**
- Accepts only `.yaml` / `.yml` files
- Validates file size (max 1MB)
- Returns user-friendly error messages for invalid files
- No files stored on disk (processed in-memory)

### Feature 7: Project Color Assignment
**Description:** Assign unique, visually distinct colors to each project.

**Implementation:** Predefined palette of 12 distinct colors, assigned in order of project appearance. Falls back to HSL generation for >12 projects.

**Acceptance Criteria:**
- Each project gets a unique color
- Colors are consistent within a single schedule
- Colors have sufficient contrast against white background

### Feature 8: Task Dependencies — Config & Parsing
**Description:** Extend the YAML parser and data models to support task
dependencies (sequential-by-default within a project, `parallel: true` opt-in,
and cross-project `depends_on`).

**Data Model Changes:**
```python
@dataclass
class Task:
    name: str
    days: int
    project: str
    task_id: str                      # "Project/Task" unique key
    depends_on: list[str]             # list of task_ids this depends on
```

**Acceptance Criteria:**
- Consecutive tasks within a project are sequential by default
- `parallel: true` on a task removes the implicit dependency on its predecessor
- `depends_on: ["Project/Task"]` adds cross-project dependencies
- Invalid dependency references raise `ValueError`
- Circular dependencies raise `ValueError`

### Feature 9: Dependency-Aware Scheduling
**Description:** Replace the simple LPT scheduler with a topological-sort-based
scheduler that respects dependency constraints.

**Algorithm:**
1. Build a dependency DAG from task `depends_on` lists.
2. Topologically sort the tasks.
3. Process tasks in topological order; for each task pick the worker whose
   `max(current_load, max(dependency_end_times), worker_availability)` is
   minimised.

**Acceptance Criteria:**
- No task starts before all its dependencies have finished
- Worker availability offsets are respected (`start >= available_in`)
- Tasks without dependencies can still be scheduled to any available worker
- Falls back to LPT behaviour when there are no dependencies

### Feature 10: Named Workers & Availability Offsets
**Description:** Allow the config to optionally name workers and specify how
many days from the start each worker becomes available.

**Config formats (both supported):**
```yaml
# Anonymous (existing)
workers: 3

# Named with optional availability
worker_names:
  - name: "Alice"
    available_in: 0
  - name: "Bob"
    available_in: 5
```

**Data Model:**
```python
@dataclass
class WorkerInfo:
    name: str
    available_in: int  # offset in working days
```

**Acceptance Criteria:**
- Named workers appear by name in the Gantt chart
- Availability offsets delay task start for that worker
- A "Current Tasks" block is rendered for the offset period
- Backward compatible — anonymous `workers: N` still works

### Feature 11: Calendar Day Display
**Description:** Display actual calendar dates on the X-axis instead of
abstract day numbers, with options for showing all days or weekdays only.

**Config:**
```yaml
calendar:
  start_date: "2026-03-09"   # defaults to today
  show_weekends: false        # default true
```

**Acceptance Criteria:**
- X-axis headers show dates (e.g. "Mon Mar 9") instead of "Day 1"
- When `show_weekends: false`, weekends are skipped — a 5-day task spans
  Mon–Fri, not Mon–Fri+Sat+Sun
- Default start date is today
- Custom start date is accepted

### Feature 12: Graphical Config Editor
**Description:** A dedicated page (`/editor`) where users can build a config
visually — add projects, tasks, workers, dependencies — and either submit it
directly or download the YAML file.

**Routes:**
| Route             | Method | Description                          |
|-------------------|--------|--------------------------------------|
| `/editor`         | GET    | Render the editor page               |
| `/editor/submit`  | POST   | Accept JSON config, return schedule  |
| `/editor/download`| POST   | Accept JSON config, return YAML file |

**Acceptance Criteria:**
- Can add/remove projects and tasks
- Can set task dependencies (intra- and cross-project)
- Can add named workers with availability offsets
- Can set calendar options
- "Generate Schedule" submits and shows the Gantt chart
- "Download YAML" returns a `.yaml` file download

## Directory Structure

```
Scheduler/
├── backend/                   # Python backend package
│   ├── __init__.py            # App factory (create_app) + public API
│   ├── models.py              # Dataclasses: Task, Config, Schedule, etc.
│   ├── parser.py              # ConfigParser — YAML parsing & validation
│   ├── scheduler.py           # TaskScheduler — dependency-aware scheduling
│   ├── colors.py              # ColorAssigner — project color palette
│   ├── calendar.py            # Calendar date computation
│   ├── editor.py              # EditorService — JSON ↔ YAML conversion
│   └── routes.py              # Flask Blueprint with all route handlers
├── assets/                    # Frontend assets
│   ├── templates/             # Jinja2 HTML templates
│   │   ├── index.html         # Landing page (upload + editor link)
│   │   ├── schedule.html      # Gantt chart display
│   │   └── editor.html        # Graphical config editor
│   ├── styles/                # CSS stylesheets
│   │   ├── common.css         # Shared reset, typography, header
│   │   ├── index.css          # Upload page styles
│   │   ├── schedule.css       # Gantt chart styles
│   │   └── editor.css         # Editor page styles
│   └── js/                    # JavaScript
│       └── editor.js          # Editor state management & rendering
├── tests/                     # pytest test suite
│   ├── test_parser.py         # YAML parsing tests (F1, F8, F10)
│   ├── test_scheduler.py      # Scheduling algorithm tests (F2, F9)
│   ├── test_colors.py         # Color assignment tests (F7)
│   ├── test_web.py            # Flask route tests (F3-F6)
│   ├── test_calendar.py       # Calendar day computation tests (F11)
│   ├── test_dep_scheduler.py  # Dependency scheduling tests (F9)
│   ├── test_dependencies.py   # Dependency parsing tests (F8)
│   ├── test_workers.py        # Named worker tests (F10)
│   └── test_editor.py         # Editor route tests (F12)
├── docs/                      # Documentation
│   ├── DESIGN.md              # This document
│   └── PROGRESS.md            # Feature progress tracking
├── configs/                   # YAML configuration files
│   └── sample_config.yaml     # Example configuration (v2 format)
├── run.py                     # Application entry point
└── requirements.txt           # Python dependencies
```

## Security Considerations

- File uploads processed in-memory only (no disk storage)
- File size limited to 1MB
- YAML safe_load used (prevents arbitrary code execution)
- File extension validation
- HTML output escaped via Jinja2 auto-escaping
