# Work Scheduler - Progress Document

## Project Overview
This document tracks the implementation progress of each feature in the Work Scheduler web application, following Red-Green Test Driven Development (TDD).

**Methodology:** For each feature:
1. Write failing tests (RED)
2. Implement the feature until tests pass (GREEN)
3. Document implementation details and test results

---

## Feature Progress Summary

| Feature | Status | Tests Written | Tests Passing |
|---------|--------|---------------|---------------|
| F1: YAML Config Parsing | Complete | 10 | 10/10 |
| F2: Task Scheduling Algorithm | Complete | 7 | 7/7 |
| F3: Flask Web Server | Complete | 5 (index) + 4 (upload) | 9/9 |
| F4: Gantt Chart Visualization | Complete | 3 | 3/3 |
| F5: Hover Tooltip Details | Complete | 3 | 3/3 |
| F6: File Upload Endpoint | Complete | 4 (shared with F3) | 4/4 |
| F7: Project Color Assignment | Complete | 6 | 6/6 |
| F8: Task Dependencies | Complete | 11 | 11/11 |
| F9: Dependency-Aware Scheduling | Complete | 8 | 8/8 |
| F10: Named Workers & Availability | Complete | 6 | 6/6 |
| F11: Calendar Day Display | Complete | 6 | 6/6 |
| F12: Graphical Config Editor | Complete | 9 | 9/9 |
| Reorganization & Refactoring | Complete | — | 77/77 |
| F13: Dual-Path Landing Page | Complete | 2 | 2/2 |
| F14: Task Indexing & Transitive Deps | Complete | 16 | 16/16 |
| F15: Phase Hierarchy | Complete | 12 | 12/12 |
| F16: Preferred Worker Allocation | Complete | 8 | 8/8 |

**Total: 115 tests, 115 passing**

---

## Feature 1: YAML Configuration Parsing

### RED Phase
Tests written in `tests/test_parser.py` covering:
- Valid YAML produces a `Config` object
- Workers count is parsed correctly
- Tasks from all projects are flattened into a single list
- Each task carries its parent project name
- Task data model has correct field types
- Missing `workers` field raises `ValueError`
- Zero workers raises `ValueError`
- Missing `projects` field raises `ValueError`
- Task missing `days` raises `ValueError`
- Negative `days` raises `ValueError`

All 10 tests failed initially with `ImportError: cannot import name 'Task' from 'work_scheduler'`.

### GREEN Phase — Implementation

**Location:** `backend/models.py` and `backend/parser.py`

**Data Models:**
Two dataclasses define the schema:
- `Task(name: str, days: int, project: str)` — a single unit of work with its parent project name attached for downstream color assignment.
- `Config(workers: int, tasks: list[Task])` — the parsed result: worker count and a flat list of all tasks across all projects.

**`parse_config(yaml_string: str) -> Config` function:**

1. Calls `yaml.safe_load()` (secure — prevents arbitrary code execution via YAML deserialization).
2. Validates `workers` exists and is a positive integer.
3. Validates `projects` exists and is a non-empty list.
4. Iterates each project, validates it has a `name` and a non-empty `tasks` list.
5. For each task, validates `name` (non-empty string) and `days` (positive integer).
6. Flattens all tasks into a single list, tagging each with its parent `project` name.
7. Returns `Config(workers=workers, tasks=tasks)`.

All validation errors raise `ValueError` with a descriptive message mentioning the problematic field.

### Test Results
```
tests/test_parser.py::TestParseConfig::test_parse_valid_config_returns_config PASSED
tests/test_parser.py::TestParseConfig::test_parse_workers_count PASSED
tests/test_parser.py::TestParseConfig::test_parse_flattens_tasks PASSED
tests/test_parser.py::TestParseConfig::test_task_has_project_name PASSED
tests/test_parser.py::TestParseConfig::test_task_fields PASSED
tests/test_parser.py::TestParseConfig::test_parse_missing_workers_raises PASSED
tests/test_parser.py::TestParseConfig::test_parse_zero_workers_raises PASSED
tests/test_parser.py::TestParseConfig::test_parse_missing_projects_raises PASSED
tests/test_parser.py::TestParseConfig::test_parse_task_missing_days_raises PASSED
tests/test_parser.py::TestParseConfig::test_parse_negative_days_raises PASSED
10 passed
```

---

## Feature 2: Task Scheduling Algorithm

### RED Phase
Tests written in `tests/test_scheduler.py` covering:
- Returns a `Schedule` object
- All tasks appear exactly once in the schedule
- No overlapping tasks per worker (sequential within a single worker)
- Scheduled duration matches the task's `days` value
- Balanced distribution across workers
- `total_days` equals the makespan (max `end_day`)
- Edge case: single task, single worker

All 7 tests failed initially with `ImportError`.

### GREEN Phase — Implementation

**Location:** `backend/scheduler.py`

**Data Models:**
- `ScheduledTask(task: Task, worker: int, start_day: int, end_day: int)` — a task placed on a specific worker's timeline. `worker` is 0-indexed, `start_day` inclusive, `end_day` exclusive.
- `Schedule(assignments: list[ScheduledTask], total_days: int)` — the complete schedule with the makespan.

**`schedule_tasks(config: Config) -> Schedule` function:**

Uses the **Longest Processing Time First (LPT)** greedy algorithm:

1. **Sort** all tasks by `days` descending — assigning longest tasks first prevents large leftover gaps.
2. **Min-heap** of `(current_end_day, worker_id)` tuples, initialized with all workers at day 0.
3. **Iterate** sorted tasks: pop the least-loaded worker, assign the task starting at that worker's current end day, push the worker back with updated end day.
4. **Makespan** is `max(end_day)` across all assignments.

**Complexity:** O(n log k) where n = number of tasks, k = number of workers (heap operations).

**Why LPT:** It's the standard heuristic for minimizing makespan on identical parallel machines, with a worst-case bound of 4/3 · OPT. Simple to implement and gives good practical results.

### Test Results
```
tests/test_scheduler.py::TestScheduleTasks::test_returns_schedule_object PASSED
tests/test_scheduler.py::TestScheduleTasks::test_all_tasks_assigned PASSED
tests/test_scheduler.py::TestScheduleTasks::test_no_overlapping_tasks_per_worker PASSED
tests/test_scheduler.py::TestScheduleTasks::test_task_duration_matches PASSED
tests/test_scheduler.py::TestScheduleTasks::test_balanced_distribution PASSED
tests/test_scheduler.py::TestScheduleTasks::test_total_days_correct PASSED
tests/test_scheduler.py::TestScheduleTasks::test_single_task_single_worker PASSED
7 passed
```

---

## Feature 3: Flask Web Server

### RED Phase
Tests written in `tests/test_web.py` → `TestIndexRoute` and `TestUploadRoute` classes covering:
- GET `/` returns 200
- Index page contains a `<form>` with `multipart/form-data` encoding
- Index page has a `type="file"` input
- POST `/upload` with valid YAML returns 200
- POST `/upload` with no file returns 400
- POST `/upload` with wrong extension returns 400
- POST `/upload` with invalid YAML content returns 400

All 7 tests failed initially with `ImportError: cannot import name 'create_app'`.

### GREEN Phase — Implementation

**Location:** `backend/routes.py`

**`create_app() -> Flask` factory function:**

Uses the Flask application factory pattern for testability:

1. Creates a `Flask` instance pointing `template_folder` at the `templates/` directory adjacent to `work_scheduler.py`.
2. Sets `MAX_CONTENT_LENGTH` to 1 MB to prevent oversized uploads.
3. Registers two routes:
   - `GET /` — renders `templates/index.html` (file upload form).
   - `POST /upload` — validates the uploaded file, parses YAML, schedules tasks, renders chart.

**Upload validation (Feature 6):**
- Checks `"file"` key exists in `request.files`.
- Checks filename is non-empty.
- Checks file extension is `.yaml` or `.yml`.
- Reads file into memory (never writes to disk).
- Parses with `parse_config()`; catches `ValueError`/`YAMLError` and returns 400 with a message escaped via `markupsafe.escape()`.

**Template:** `templates/index.html` — minimal form with drag-and-drop-style file input, `accept=".yaml,.yml"` for browser filtering, and a submit button.

### Test Results
```
tests/test_web.py::TestIndexRoute::test_index_returns_200 PASSED
tests/test_web.py::TestIndexRoute::test_index_contains_upload_form PASSED
tests/test_web.py::TestIndexRoute::test_index_has_file_input PASSED
tests/test_web.py::TestUploadRoute::test_upload_valid_yaml_returns_200 PASSED
tests/test_web.py::TestUploadRoute::test_upload_no_file_returns_error PASSED
tests/test_web.py::TestUploadRoute::test_upload_wrong_extension_returns_error PASSED
tests/test_web.py::TestUploadRoute::test_upload_invalid_yaml_returns_error PASSED
7 passed
```

---

## Feature 4: Gantt Chart Visualization

### RED Phase
Tests written in `tests/test_web.py` → `TestGanttChartRendering` class covering:
- Schedule page contains "Worker 1" label
- Schedule page contains `task-block` CSS class
- Schedule page contains day header numbers

All 3 tests failed before the template was created.

### GREEN Phase — Implementation

**Location:** `templates/schedule.html`

**Rendering approach:** Server-side CSS Grid via Jinja2 — no JavaScript library needed.

**Grid layout:**
- `grid-template-columns: 100px repeat(N, minmax(40px, 1fr))` — 1 label column + N day columns.
- `grid-template-rows: auto repeat(W, 44px)` — 1 header row + W worker rows.

**Header row:** Blank corner cell + "Day 1" through "Day N" cells.

**Worker rows:** For each worker (0 to W-1):
1. Worker label cell ("Worker 1", "Worker 2", ...).
2. Iterate that worker's assignments sorted by `start_day`.
3. Fill empty cells for gaps between tasks.
4. Render each task as a `<div class="task-block">` with `grid-column: span D` where D = task days.
5. Background color set via inline `style` from the project color map.
6. Fill trailing empty cells to complete the row.

**Scrollability:** `overflow-x: auto` on the wrapper for large schedules.

### Test Results
```
tests/test_web.py::TestGanttChartRendering::test_schedule_contains_worker_labels PASSED
tests/test_web.py::TestGanttChartRendering::test_schedule_contains_task_blocks PASSED
tests/test_web.py::TestGanttChartRendering::test_schedule_contains_day_headers PASSED
3 passed
```

---

## Feature 5: Hover Tooltip Details

### RED Phase
Tests written in `tests/test_web.py` → `TestTooltips` class covering:
- HTML contains the task name "Setup DB"
- HTML contains the project name "Backend API"
- HTML contains the CSS class "tooltip"

All 3 tests failed before tooltip markup was added.

### GREEN Phase — Implementation

**Location:** `templates/schedule.html`, inside each `.task-block` div

**Approach:** Pure CSS tooltips — no JavaScript required.

Each task block contains a `<span class="tooltip">` child with:
- **Task name** (bold)
- **Project name**
- **Duration** in days
- **Day range** (start–end)

**CSS mechanics:**
- `.tooltip` is `visibility: hidden; opacity: 0` by default.
- `.task-block:hover .tooltip` sets `visibility: visible; opacity: 1`.
- Positioned above the task block with `bottom: calc(100% + 8px)` and centered with `transform: translateX(-50%)`.
- A CSS `::after` pseudo-element creates an arrow pointing down.
- `transition: opacity 0.15s` provides a smooth fade-in.
- `pointer-events: none` prevents the tooltip from interfering with hover state.

### Test Results
```
tests/test_web.py::TestTooltips::test_tooltip_contains_task_name PASSED
tests/test_web.py::TestTooltips::test_tooltip_contains_project_name PASSED
tests/test_web.py::TestTooltips::test_tooltip_css_exists PASSED
3 passed
```

---

## Feature 6: File Upload Endpoint

### RED Phase
Tests shared with Feature 3 in `TestUploadRoute`:
- No file → 400
- Wrong extension (.txt) → 400
- Invalid YAML content → 400
- Valid YAML → 200

### GREEN Phase — Implementation

**Location:** `backend/routes.py`, `/upload` route handler

**Validation pipeline:**
1. **Presence check:** `"file" in request.files` → 400 "No file uploaded"
2. **Filename check:** `file.filename` is non-empty → 400 "No file selected"
3. **Extension check:** `os.path.splitext(filename)[1].lower()` in `{".yaml", ".yml"}` → 400 "Only .yaml / .yml files are accepted"
4. **Size limit:** Flask's `MAX_CONTENT_LENGTH = 1MB` automatically returns 413 for oversized files.
5. **Content parsing:** `file.read()` → `parse_config(decoded_string)` — catches `ValueError`/`YAMLError` → 400 with escaped error message.

**Security:**
- File is read into memory and never written to disk.
- `yaml.safe_load()` prevents YAML deserialization attacks.
- Error messages are escaped with `markupsafe.escape()` to prevent XSS.
- Jinja2 auto-escaping is enabled by default.

### Test Results
```
tests/test_web.py::TestUploadRoute::test_upload_no_file_returns_error PASSED
tests/test_web.py::TestUploadRoute::test_upload_wrong_extension_returns_error PASSED
tests/test_web.py::TestUploadRoute::test_upload_invalid_yaml_returns_error PASSED
tests/test_web.py::TestUploadRoute::test_upload_valid_yaml_returns_200 PASSED
4 passed
```

---

## Feature 7: Project Color Assignment

### RED Phase
Tests written in `tests/test_colors.py` covering:
- Returns a dict
- Each project gets a unique color
- All project names present as keys
- Color format is valid CSS (hex or hsl)
- 20 projects still produce 20 unique colors
- Edge case: single project

All 6 tests failed initially with `ImportError`.

### GREEN Phase — Implementation

**Location:** `backend/colors.py`

**Predefined palette:** 12 hand-picked hex colors from the Tableau 10 + 2 extra palette, chosen for mutual contrast and readability on white backgrounds:
```
#4e79a7, #f28e2b, #e15759, #76b7b2, #59a14f, #edc948,
#b07aa1, #ff9da7, #9c755f, #bab0ac, #6b6ecf, #d67195
```

**`assign_project_colors(project_names: list[str]) -> dict[str, str]`:**
1. For projects 0–11: assign from the predefined palette.
2. For projects 12+: generate HSL colors with `hue = (360/n) * i`, saturation 65%, lightness 55% — evenly spaced around the color wheel for maximum distinction.
3. Returns a dict mapping project name → CSS color string.

**Integration:** Called in the `/upload` route handler. The color map is passed to the Jinja2 template, where each task block's `background-color` is set via inline style.

### Test Results
```
tests/test_colors.py::TestAssignProjectColors::test_returns_dict PASSED
tests/test_colors.py::TestAssignProjectColors::test_unique_colors_per_project PASSED
tests/test_colors.py::TestAssignProjectColors::test_all_projects_have_colors PASSED
tests/test_colors.py::TestAssignProjectColors::test_color_format_is_valid PASSED
tests/test_colors.py::TestAssignProjectColors::test_many_projects_still_unique PASSED
tests/test_colors.py::TestAssignProjectColors::test_single_project PASSED
6 passed
```

---

## Final Integration Test

All 79 tests passing:

```
tests/test_calendar.py      6 passed
tests/test_colors.py        6 passed
tests/test_dep_scheduler.py  8 passed
tests/test_dependencies.py  11 passed
tests/test_editor.py        9 passed
tests/test_parser.py       10 passed
tests/test_scheduler.py     7 passed
tests/test_web.py          16 passed
tests/test_workers.py       6 passed
===== 79 passed =====
```

---

## Feature 8: Task Dependencies

### RED Phase
Tests written in `tests/test_dependencies.py` covering:
- Sequential by default: second task depends on first, third on second
- First task has no dependencies
- Task ID format is "Project/Task"
- Parallel opt-in: parallel task does not depend on predecessor
- Parallel task inherits predecessor's dependencies
- First task with parallel flag has no deps
- Cross-project dependency via `depends_on`
- Combined implicit and explicit dependencies
- Invalid dependency reference raises `ValueError`
- Circular dependency raises `ValueError`

All 11 tests failed initially.

### GREEN Phase — Implementation

**Location:** `backend/parser.py`, `ConfigParser.parse()` method

**Sequential-by-default:** When iterating tasks within a project, each task (except the first) automatically depends on the previous task. This minimizes config verbosity — no explicit linking needed for the common sequential case.

**Parallel opt-in:** If `parallel: true`, the task does NOT depend on its predecessor. Instead it inherits the predecessor's dependencies, running in parallel with it.

**Cross-project:** `depends_on: ["OtherProject/TaskName"]` adds explicit dependencies across projects. These combine with implicit sequential deps.

**Validation:**
- All `depends_on` references are checked against the global task map. Invalid references raise `ValueError`.
- Circular dependency detection via `_detect_circular()` using Kahn's algorithm (BFS-based topological sort — if the number of visited nodes is less than the total number of tasks, a cycle exists).

**Task ID format:** `"{ProjectName}/{TaskName}"` — unique across all projects.

### Test Results
```
tests/test_dependencies.py — 11 passed
```

---

## Feature 9: Dependency-Aware Scheduling

### RED Phase
Tests written in `tests/test_dep_scheduler.py` covering:
- Dependent task starts after predecessor finishes
- Parallel tasks can overlap (run simultaneously)
- Cross-project dependency is respected
- Diamond dependency pattern works correctly
- No dependencies falls back to balanced LPT scheduling
- Worker availability offset delays task start
- Max(dependency_end, worker_availability) determines start
- Worker availability blocks appear in schedule data

All 8 tests failed initially.

### GREEN Phase — Implementation

**Location:** `backend/scheduler.py`, `TaskScheduler.schedule()` method

**Algorithm:** Topological sort (Kahn's algorithm) with LPT tiebreaking:

1. Build an in-degree map and adjacency list from the dependency graph.
2. Initialize a ready queue with zero-in-degree tasks, sorted by days descending (LPT).
3. Pop the task with the longest duration from the ready queue.
4. Find the earliest available worker, considering:
   - Worker's current end time
   - Worker's `available_in` offset (from `WorkerInfo`)
   - Maximum of all dependency end times
   - Final start = `max(worker_end, worker_available_in, max_dep_end)`
5. Assign the task, push the worker back to the heap, decrement in-degrees of successors.
6. When successor in-degree reaches 0, add it to the ready queue.
7. Repeat until all tasks are scheduled.

**Worker availability (Option A):** `start = max(dependency_end, worker_availability)` — the worker physically cannot begin until their offset day, regardless of when dependencies finish. "Current Tasks" blocks are represented in the schedule data for UI rendering.

### Test Results
```
tests/test_dep_scheduler.py — 8 passed
```

---

## Feature 10: Named Workers with Availability

### RED Phase
Tests written in `tests/test_workers.py` covering:
- Named workers parsed from `worker_names` list
- `available_in` defaults to 0 when omitted
- Anonymous `workers: N` still works (backward compatible)
- Worker count derived from length of `worker_names`
- Negative `available_in` raises `ValueError`
- Missing both `workers` and `worker_names` raises `ValueError`

All 6 tests failed initially.

### GREEN Phase — Implementation

**Location:** `backend/models.py` + `backend/parser.py`

**Data Model:** `WorkerInfo(name: str, available_in: int = 0)` — each worker has a display name and an optional day offset before they become available.

**Parsing:** `worker_names` takes priority over `workers`. Each entry must have a `name` string. `available_in` defaults to 0. Negative values raise `ValueError`. When `workers: N` is used instead, generates `WorkerInfo("Worker 1"), ..., WorkerInfo("Worker N")`.

**Config expanded:** `Config` now holds `worker_names: list[WorkerInfo]` alongside `workers: int` (count). Schedule also carries `worker_names` for template rendering.

**UI rendering:** Worker labels show actual names instead of "Worker N". Workers with `available_in > 0` display a hatched "Current Tasks" block spanning that many days at the start of their row.

### Test Results
```
tests/test_workers.py — 6 passed
```

---

## Feature 11: Calendar Day Display

### RED Phase
Tests written in `tests/test_calendar.py` covering:
- Calendar section parsed from YAML
- Defaults: `start_date=today`, `show_weekends=True`
- Weekdays-only skips Sat/Sun
- All-days includes weekends
- Zero total days returns empty list
- Start on weekend with weekdays-only advances to Monday

All 6 tests failed initially.

### GREEN Phase — Implementation

**Location:** `backend/calendar.py` + `backend/models.py`

**Data Model:** `CalendarSettings(start_date: date = today, show_weekends: bool = True)`

**`compute_calendar_dates(settings, total_days) -> list[date]`:**
1. Start from `settings.start_date`.
2. For each of `total_days` working days, advance one day at a time.
3. If `show_weekends=False`, skip Saturday (5) and Sunday (6).
4. Return list of `date` objects corresponding to each working day.

**Template integration:** When `calendar_dates` is available, day headers show `"Mon\nMar 09"` format instead of `"Day 1"`. Tooltips show date ranges instead of day numbers.

### Test Results
```
tests/test_calendar.py — 6 passed
```

---

## Feature 12: Graphical Config Editor

### RED Phase
Tests written in `tests/test_editor.py` covering:
- GET `/editor` returns 200
- Editor page has project controls ("Add Project" or "add-project")
- Editor page has worker controls
- POST `/editor/submit` with valid JSON returns 200
- Submit returns HTML with `task-block` class
- Submit with empty body returns 400
- POST `/editor/download` returns YAML content type
- Downloaded YAML is valid and contains `projects`
- Download response has `Content-Disposition: attachment` header

All 9 tests failed initially.

### GREEN Phase — Implementation

**Location:** `backend/routes.py` + `backend/editor.py` + `assets/templates/editor.html`

**Backend routes:**
- `GET /editor` — renders the editor template
- `POST /editor/submit` — accepts JSON config, converts to `Config` via `_json_to_config()`, schedules, returns rendered `schedule.html`
- `POST /editor/download` — accepts JSON config, converts to YAML string via `_json_to_yaml_string()`, returns as downloadable `config.yaml` attachment

**`_json_to_yaml_string(data)`:** Converts the editor JSON payload into a clean YAML string, preserving only relevant fields (worker names, calendar settings, projects with tasks, dependencies, parallel flags).

**`_json_to_config(data)`:** Round-trips through YAML → `parse_config()` to reuse the battle-tested parsing and validation logic.

**Editor UI (`templates/editor.html`):**
- **Workers panel:** Add/remove named workers, set name and `available_in` offset per worker.
- **Calendar panel:** Date picker for start date, checkbox for show weekends.
- **Projects panel:** Add/remove projects, each with add/remove tasks. Each task has name, days, parallel checkbox, and dependency selector (dropdown populated from all task IDs across projects).
- **Actions:** "Generate Schedule" (submits JSON, replaces page with Gantt chart) and "Download YAML" (downloads config file).
- Pure JavaScript — no framework dependencies. XSS-safe via DOM `textContent` escaping.

### Test Results
```
tests/test_editor.py — 9 passed
```

---

## Project Reorganization & Refactoring

### Summary

Restructured the entire project from a single-file monolith (`work_scheduler.py`) into a well-organized multi-module architecture with separated frontend assets.

### Backend Refactoring

The monolithic `work_scheduler.py` was split into a `backend/` Python package with classes in separate modules:

| Module | Class / Contents | Responsibility |
|--------|-----------------|----------------|
| `models.py` | `Task`, `WorkerInfo`, `CalendarSettings`, `Config`, `ScheduledTask`, `Schedule` | All dataclass definitions |
| `parser.py` | `ConfigParser` | YAML parsing, validation, dependency resolution, cycle detection |
| `scheduler.py` | `TaskScheduler` | Topological sort + greedy worker assignment |
| `colors.py` | `ColorAssigner` | Project color palette assignment |
| `calendar.py` | `compute_calendar_dates()` | Calendar date mapping with weekend handling |
| `editor.py` | `EditorService` | JSON ↔ YAML conversion for the editor |
| `routes.py` | `main_bp` (Flask Blueprint) | All HTTP route handlers |
| `__init__.py` | `create_app()` factory | App factory + public API re-exports |

Each class uses `@staticmethod` / `@classmethod` methods with convenience aliases (e.g., `parse_config = ConfigParser.parse`) for backward-compatible imports.

### Frontend Refactoring

Inline CSS and JavaScript were extracted from HTML templates into separate files:

| File | Extracted From |
|------|---------------|
| `assets/styles/common.css` | Shared reset, typography, header styles (from all templates) |
| `assets/styles/index.css` | Upload page styles (from `index.html`) |
| `assets/styles/schedule.css` | Gantt chart + tooltip styles (from `schedule.html`) |
| `assets/styles/editor.css` | Editor form/panel styles (from `editor.html`) |
| `assets/js/editor.js` | Editor state management + rendering logic (from `editor.html`) |

HTML templates now use `<link rel="stylesheet" href="{{ url_for('static', ...) }}">` and `<script src="{{ url_for('static', ...) }}">` for external assets.

### Directory Structure

```
Scheduler/
├── backend/                    # Python package
│   ├── __init__.py             # App factory + re-exports
│   ├── models.py               # Dataclasses
│   ├── parser.py               # ConfigParser
│   ├── scheduler.py            # TaskScheduler
│   ├── colors.py               # ColorAssigner
│   ├── calendar.py             # Calendar computation
│   ├── editor.py               # EditorService
│   └── routes.py               # Flask Blueprint
├── assets/                     # Frontend assets
│   ├── templates/              # Jinja2 HTML templates
│   │   ├── index.html
│   │   ├── schedule.html
│   │   └── editor.html
│   ├── styles/                 # CSS stylesheets
│   │   ├── common.css
│   │   ├── index.css
│   │   ├── schedule.css
│   │   └── editor.css
│   └── js/
│       └── editor.js
├── tests/                      # 9 test files (imports updated)
├── docs/                       # DESIGN.md + PROGRESS.md
├── configs/                    # YAML config files
│   └── sample_config.yaml
├── run.py                      # Entry point
└── requirements.txt
```

### Test Verification

All 77 tests pass after restructuring with updated imports (`from backend import ...`):

```
tests/test_calendar.py       6 passed
tests/test_colors.py         6 passed
tests/test_dep_scheduler.py  8 passed
tests/test_dependencies.py  11 passed
tests/test_editor.py         9 passed
tests/test_parser.py        10 passed
tests/test_scheduler.py      7 passed
tests/test_web.py           14 passed
tests/test_workers.py        6 passed
===== 77 passed =====
```

---

## Feature 13: Dual-Path Landing Page

### RED Phase
Tests written in `tests/test_web.py` → `TestIndexRoute` class, added:
- Landing page contains a link to `/editor`
- Landing page contains an "or" divider between upload and editor options

Both tests failed before the template was updated.

### GREEN Phase — Implementation

**Landing page (`index.html`):**

Redesigned from a single upload form into a dual-option layout:
1. **Upload a Config File** — the existing file upload form, unchanged.
2. **"or" divider** — a horizontal rule with centered text separating the two options.
3. **Build in the Editor** — descriptive text and a prominent green button linking to `/editor`.

This allows users to either upload an existing YAML config or construct one visually in the editor, without requiring a config file to access the rest of the application.

**Navigation updates:**
- Schedule page: "Upload file" back link changed to "Home"
- Editor page: "Upload file" back link changed to "Home"

**CSS (`index.css`):**
- Added `.option-section` for grouping each option with its own heading.
- Added `.divider` with `::before`/`::after` pseudo-elements for the horizontal line with centered "or" text.
- Added `.btn-editor` styled as a green call-to-action button.

### Test Results
```
tests/test_web.py::TestIndexRoute::test_index_has_editor_link PASSED
tests/test_web.py::TestIndexRoute::test_index_has_or_divider PASSED
2 new tests, 79 total passed
```

---

## Feature 14: Task Indexing & Transitive Dependencies

### RED Phase
Tests written in `tests/test_indexing.py` covering:
- **TestIndexParsing (4):** Index stored on task, sequential indexes create dependency, first index has no deps, task_id format correct.
- **TestInvalidIndex (2):** Non-alphanumeric index rejected, letter-only index rejected.
- **TestParallelSiblings (4):** Same-number siblings share predecessor deps, don't depend on each other, successors depend on all siblings, siblings overlap in schedule.
- **TestTransitiveDependencies (2):** Chain A→B→C: C inherits A transitively, B has direct dep only.
- **TestTransitiveWithExplicitDeps (1):** Cross-project explicit dep inherits transitive deps.
- **TestNoImplicitCrossOrdering (2):** Same index in different projects are independent, can schedule in parallel.
- **TestIndexGaps (1):** Non-consecutive indexes (1→5) produce no implicit dep.

### GREEN Phase — Implementation

**Index format:** `_INDEX_RE = re.compile(r"^(\d+)([A-Za-z]?)$")` validates indexes as number or number+letter (e.g. `1`, `2`, `1A`, `1B`).

**`_parse_indexed_tasks()` in `parser.py`:**
- Groups tasks by numeric prefix.
- Index N auto-depends on all tasks at index N-1.
- Parallel siblings (same number, different letter) share deps but don't depend on each other.
- Explicit `depends_on` is merged with implicit deps.

**`_transitive_close()` in `parser.py`:**
- Computes transitive closure in topological order.
- After closure, each task's `depends_on` includes ALL direct and indirect dependencies.
- The scheduler benefits from the full dependency set for correct earliest-start computation.

**Format detection:** `_parse_task_list()` checks for any `index` field to distinguish v3 (indexed) from v1/v2 (sequential) task lists, preserving full backward compatibility.

### Test Results
```
tests/test_indexing.py — 16 passed
```

---

## Feature 15: Phase Hierarchy

### RED Phase
Tests written in `tests/test_phases.py` covering:
- **TestPhaseParsing (4):** Task ID includes phase, all tasks parsed, intra-phase sequential deps, cross-phase independence.
- **TestPhaseLevelDependency (2):** Phase dep expands to all tasks in phase, schedule respects phase dep.
- **TestMixedProjects (2):** Phased and flat projects coexist, flat tasks can depend on phased tasks.
- **TestPhaseValidation (3):** Empty phase tasks raise, missing phase name raises, invalid phase dep reference raises.
- **TestCrossProjectPhaseDep (1):** Phase deps can span projects.

### GREEN Phase — Implementation

**Task ID format:** `"Project/Phase/Task"` for phased projects, `"Project/Task"` for flat projects.

**Phase parsing in `ConfigParser.parse()`:**
- Projects can have `phases` (list of phase dicts with `name` + `tasks`) or flat `tasks`.
- `phase_tasks` dict maps `"Project/Phase"` → list of task_ids.

**Phase-level dependency resolution:**
- If `depends_on` contains a key matching a phase_id (e.g. `"App/Research"`), it expands to all task_ids in that phase.
- Combined with transitive closure, downstream tasks correctly inherit all ancestor dependencies.

### Test Results
```
tests/test_phases.py — 12 passed
```

---

## Feature 16: Preferred Worker Allocation

### RED Phase
Tests written in `tests/test_preferred.py` covering:
- **TestPreferredWorkerParsing (2):** preferred_workers stored, empty defaults to empty list.
- **TestPreferredWorkerScheduling (4):** Preferred chosen when tied, preference doesn't sacrifice start time, fallback when busy, multiple preferred workers.
- **TestPreferredWithAvailability (2):** Available-later preferred not chosen, same-availability preferred wins.

### GREEN Phase — Implementation

**Model:** `Task.preferred_workers: list[str]` — optional list of worker names.

**Scheduler algorithm in `scheduler.py`:**
1. For each task, compute `best_start` across all workers.
2. Collect all workers tied at `best_start`.
3. If any tied worker is in `task.preferred_workers`, choose the first preferred.
4. Otherwise, fall back to the first tied worker.

This ensures preferred workers are favoured **only when they don't increase makespan** — the scheduler never delays a task to wait for a preferred worker.

**Editor support (`editor.py`):** `_task_entry()` helper emits `preferred_workers` and `index` fields in YAML output.

### Test Results
```
tests/test_preferred.py — 8 passed
```
