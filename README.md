# Work Scheduler

A locally-hosted web application that schedules tasks across workers and
displays the result as an interactive Gantt chart. Users can upload a YAML
configuration file or build one visually in the graphical editor.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![Flask 3.0+](https://img.shields.io/badge/flask-3.0%2B-green)
![Tests 79 passing](https://img.shields.io/badge/tests-79%20passing-brightgreen)

---

## Features

- **YAML config parsing** — define workers, projects, tasks, dependencies,
  and calendar settings in a structured YAML file.
- **Graphical config editor** — build a configuration visually in the browser
  with a form-based UI (no YAML knowledge needed).
- **Dependency-aware scheduling** — tasks within a project are sequential by
  default; use `parallel: true` to opt in to concurrency. Cross-project
  `depends_on` references are also supported.
- **LPT load balancing** — the scheduler uses Longest Processing Time First
  to minimize makespan across workers.
- **Interactive Gantt chart** — server-rendered CSS Grid chart with worker
  swimlanes, colored task blocks per project, and hover tooltips showing
  task details.
- **Named workers with availability offsets** — assign names to workers and
  specify how many days until each becomes available.
- **Calendar dates** — display real calendar dates on the X-axis with
  optional weekday-only mode (skip weekends).
- **YAML download** — export the editor's configuration as a downloadable
  `.yaml` file.
- **Dual-path landing page** — users can upload an existing config file or
  jump straight to the editor.

---

## Quick Start

### Prerequisites

- Python 3.10 or later
- `pip` (comes with Python)

### Installation

```bash
# Clone or download the repository
cd Scheduler

# Create a virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
python run.py
```

The server starts at **http://localhost:5000**.  Open it in a browser to:

1. **Upload** an existing YAML config file, or
2. **Open the Editor** to build a config from scratch.

### Running Tests

```bash
python -m pytest tests/ -v
```

All 79 tests should pass.

---

## YAML Configuration Format

The scheduler accepts two configuration styles. Both can be combined.

### Simple (v1)

```yaml
workers: 3

projects:
  - name: "Backend API"
    tasks:
      - name: "Setup database"
        days: 3
      - name: "Build endpoints"
        days: 5
  - name: "Frontend"
    tasks:
      - name: "Mockups"
        days: 2
```

### Full (v2) — dependencies, named workers, calendar

```yaml
worker_names:
  - name: "Alice"
    available_in: 0
  - name: "Bob"
    available_in: 5
  - name: "Charlie"

calendar:
  start_date: "2026-03-09"
  show_weekends: false

projects:
  - name: "Backend API"
    tasks:
      - name: "Setup database"
        days: 3
      - name: "Build endpoints"      # sequential (depends on previous)
        days: 5
      - name: "Write docs"
        parallel: true                # runs alongside "Build endpoints"
        days: 2

  - name: "Frontend"
    tasks:
      - name: "Mockups"
        days: 2
      - name: "Dashboard"
        days: 4
        depends_on:
          - "Backend API/Build endpoints"   # cross-project dependency
```

A sample config is provided at `configs/sample_config.yaml`.

---

## Project Structure

```
Scheduler/
├── backend/                   # Python backend package
│   ├── __init__.py            # App factory (create_app) + public API re-exports
│   ├── models.py              # Dataclasses: Task, Config, Schedule, WorkerInfo, etc.
│   ├── parser.py              # YAML parsing, validation, dependency resolution
│   ├── scheduler.py           # Dependency-aware scheduling (Kahn's + LPT)
│   ├── colors.py              # Project color palette assignment
│   ├── calendar.py            # Calendar date computation with weekend handling
│   ├── editor.py              # JSON ↔ YAML conversion for the graphical editor
│   └── routes.py              # Flask Blueprint with all HTTP route handlers
├── assets/                    # Frontend assets (served as Flask static files)
│   ├── templates/             # Jinja2 HTML templates
│   │   ├── index.html         # Landing page — upload form + editor link
│   │   ├── schedule.html      # Gantt chart display with tooltips
│   │   └── editor.html        # Graphical config editor
│   ├── styles/                # CSS stylesheets
│   │   ├── common.css         # Shared reset, typography, header navigation
│   │   ├── index.css          # Landing page styles
│   │   ├── schedule.css       # Gantt chart, tooltips, legend styles
│   │   └── editor.css         # Editor form, panel, and button styles
│   └── js/
│       └── editor.js          # Editor state management, rendering, submissions
├── tests/                     # pytest test suite (79 tests)
│   ├── test_parser.py         # YAML parsing tests
│   ├── test_scheduler.py      # Scheduling algorithm tests
│   ├── test_colors.py         # Color assignment tests
│   ├── test_web.py            # Flask route + template rendering tests
│   ├── test_calendar.py       # Calendar date computation tests
│   ├── test_dep_scheduler.py  # Dependency-aware scheduling tests
│   ├── test_dependencies.py   # Dependency parsing tests
│   ├── test_workers.py        # Named worker parsing tests
│   └── test_editor.py         # Editor route tests
├── docs/                      # Documentation
│   ├── DESIGN.md              # Architecture, features, and design decisions
│   ├── PROGRESS.md            # Feature-by-feature TDD progress log
│   └── AUDIT.md               # Project audit (code quality, security, etc.)
├── configs/
│   └── sample_config.yaml     # Example configuration (v2 format)
├── run.py                     # Application entry point
└── requirements.txt           # Python dependencies
```

---

## Routes

| Route              | Method | Description                                      |
|--------------------|--------|--------------------------------------------------|
| `/`                | GET    | Landing page — upload a config or open the editor |
| `/upload`          | POST   | Accept a YAML file, parse, schedule, render chart |
| `/editor`          | GET    | Graphical configuration editor                    |
| `/editor/submit`   | POST   | Accept editor JSON, schedule, render chart        |
| `/editor/download` | POST   | Accept editor JSON, return YAML file download     |

---

## Dependencies

| Package  | Version | Purpose                    |
|----------|---------|----------------------------|
| Flask    | >= 3.0  | Web framework              |
| PyYAML   | >= 6.0  | YAML parsing               |
| pytest   | >= 8.0  | Test framework (dev only)  |

---

## Possible Future Features

- **Persistent storage** — save and load schedules from a database or
  local file system so users can revisit past schedules.
- **Export options** — export the Gantt chart as a PNG, SVG, or PDF image.
- **Drag-and-drop editor** — allow repositioning tasks directly on the
  Gantt chart with drag-and-drop.
- **Multi-user collaboration** — real-time editing with WebSockets so
  multiple users can build a config together.
- **Resource constraints** — model worker skills or equipment so that
  only certain workers can perform certain tasks.
- **Cost tracking** — add per-worker or per-task cost fields and display
  budget summaries alongside the schedule.
- **Undo/redo in editor** — maintain an action history stack for the
  graphical editor.
- **Import from project management tools** — import tasks from Jira,
  Trello, or CSV files.
- **Critical path highlighting** — visually highlight the critical path
  through the dependency graph on the Gantt chart.
- **Dark mode** — add a dark color scheme toggle.

---

## License

This project is licensed under the [MIT License](LICENSE).
