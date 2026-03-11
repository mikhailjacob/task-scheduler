# Work Scheduler — Project Audit

**Date:** March 10, 2026
**Scope:** Full audit of design, code, frontend, tests, documentation, and security.
**Revision:** 2 — updated after F14 (Task Indexing), F15 (Phase Hierarchy), F16 (Preferred Workers).

---

## Table of Contents

1. [Architecture & Design](#1-architecture--design)
2. [Backend Code Quality](#2-backend-code-quality)
3. [Frontend Code Quality](#3-frontend-code-quality)
4. [Test Suite](#4-test-suite)
5. [Security Analysis](#5-security-analysis)
6. [Performance Considerations](#6-performance-considerations)
7. [Documentation](#7-documentation)
8. [Dependency Health](#8-dependency-health)
9. [Findings Summary](#9-findings-summary)

---

## 1. Architecture & Design

### 1.1 Overall Structure — PASS

The project follows a clean layered architecture:

- **Backend package** (`backend/`) with single-responsibility modules.
- **Frontend assets** separated into templates, styles, and scripts.
- **Tests** isolated in their own directory with one file per feature area.
- **Documentation** in `docs/` with design and progress tracking.

The Flask application factory pattern (`create_app()`) is used correctly,
enabling testability and configuration flexibility.

### 1.2 Module Design — PASS

| Module        | Responsibility                  | Coupling | Verdict |
|---------------|---------------------------------|----------|---------|
| `models.py`   | Pure dataclasses, no logic      | None     | Clean   |
| `parser.py`   | YAML parsing + validation       | models   | Clean   |
| `scheduler.py`| Scheduling algorithm            | models   | Clean   |
| `colors.py`   | Color assignment                | None     | Clean   |
| `calendar.py` | Date computation                | models   | Clean   |
| `editor.py`   | JSON → YAML conversion          | parser   | Clean   |
| `routes.py`   | HTTP handlers (thin controller) | All      | Expected|

Each module depends only downward on `models` and/or `parser`. The route
handlers in `routes.py` act as a thin controller layer that ties the
modules together — this is appropriate for the project's scope.

### 1.3 Data Flow — PASS

```
YAML string / Editor JSON
    ↓
ConfigParser.parse() / EditorService.json_to_config()
    ↓
Config (validated) — with transitive dependency closure
    ↓
TaskScheduler.schedule()  — preferred worker selection
    ↓
Schedule
    ↓
_build_schedule_context()  →  colors, calendar dates
    ↓
Jinja2 template rendering  →  HTML response
```

The pipeline is linear and easy to trace. Each stage has a clear input/output
contract defined by the dataclasses.

### 1.4 Design Observations

| Item | Status | Notes |
|------|--------|-------|
| Separation of concerns | Good | Each module has a single purpose |
| Flask Blueprint usage | Good | Routes are registered via Blueprint, not directly on the app |
| Convenience aliases | Good | `parse_config = ConfigParser.parse` keeps client code clean |
| `__all__` export list | Good | Explicit public API in `__init__.py` |
| No circular imports | Good | Import graph is acyclic |
| v1/v2/v3 format compat | Good | Parser auto-detects format; older configs continue to work |

---

## 2. Backend Code Quality

### 2.1 Python Style — PASS

- Consistent use of `from __future__ import annotations` for modern type hints.
- All modules and classes have docstrings.
- Type hints on all public function signatures.
- Dataclasses use `field(default_factory=...)` correctly for mutable defaults.
- No bare `except` clauses; exception handling is specific (`ValueError`, `yaml.YAMLError`).
- Line lengths are reasonable (under 90 characters generally).

### 2.2 Algorithm Correctness — PASS

**Parser** (`parser.py`):
- YAML is loaded with `yaml.safe_load()` — prevents arbitrary code execution.
- All required fields are validated with specific error messages.
- v3 index format validated with compiled regex `_INDEX_RE`.
- Dependency references are validated against known task IDs and phase IDs.
- Phase-level dependencies correctly expanded before validation.
- Circular dependency detection uses Kahn's algorithm (BFS topological sort) —
  correct: if `visited != len(tasks)`, a cycle exists.
- v1/v2 sequential-by-default / parallel opt-in logic preserved for backward compat.
- v3 indexed tasks: same-number parallel siblings, N depends on N-1, correct.
- Transitive closure computed via topological propagation — correct.

**Scheduler** (`scheduler.py`):
- Kahn's algorithm for topological sort is implemented correctly.
- LPT tiebreaking (longest task first from the ready queue via min-heap of
  negated durations) is correct.
- Worker selection considers `max(worker_end, dep_end)` for each worker —
  correct for minimizing worker start time.
- Preferred worker selection only among tied workers — does not sacrifice makespan.
- Edge cases handled: zero tasks (returns `total_days=0`), single task/worker.

**Calendar** (`calendar.py`):
- Weekend skip logic checks `weekday() >= 5` — correct (Saturday=5, Sunday=6).
- Start-on-weekend advancement to Monday is correct.
- Zero total days returns empty list.

### 2.3 Observations

| Item | Status | Notes |
|------|--------|-------|
| Duplicate task IDs | Minor gap | If two tasks in the same project/phase share a name, the task_id will collide silently. The parser does not enforce unique task names within a project/phase. Low risk for typical usage. |
| Duplicate task names across phases | Note | WS Phases 4A/4B/4C each have identically-named tasks ("ML 2D invisible prototype"). This works because task IDs include the phase name, but users could find it confusing in the Gantt chart. |
| Worker selection is O(k) per task | Acceptable | The scheduler iterates all workers for each task. For typical project sizes (< 100 workers), this is fine. |
| EditorService round-trip | By design | `json_to_config` serializes to YAML then parses it back. Slightly redundant but ensures the editor path uses the same validation as file upload. |
| `preferred_workers` not validated against worker names | Minor gap | The parser does not check that `preferred_workers` entries match actual worker names. Invalid names are silently ignored by the scheduler. |

---

## 3. Frontend Code Quality

### 3.1 HTML Templates — PASS

- All templates are valid HTML5 with proper `lang`, `charset`, and `viewport` meta tags.
- External CSS and JS loaded via `url_for('static', ...)` — correct for Flask.
- Jinja2 variable output uses double-brace `{{ }}` syntax, which auto-escapes
  by default — good XSS protection.
- Templates are focused: each page has its own template with no unnecessary duplication.

### 3.2 CSS — PASS

- Styles are cleanly separated: `common.css` for shared styles, page-specific
  files for the rest.
- CSS Grid is used appropriately for the Gantt chart layout.
- Responsive considerations: `overflow-x: auto` on the chart wrapper, flexible
  widths on form elements.
- No vendor prefixes needed — the targeted features (CSS Grid, flexbox) have
  excellent browser support.

### 3.3 JavaScript (`editor.js`) — PARTIAL PASS

- Pure vanilla JS with no framework dependencies — appropriate for the project scope.
- State management is simple and clear: `workers` and `projects` arrays.
- XSS protection via the `esc()` function which uses `textContent` encoding —
  correct approach for DOM-based escaping.
- `fetch` calls include proper error handling with `.catch()`.
- JSDoc comments on all public functions.

**Issue: Editor JS is out of date with v3 backend.**
The editor JS still uses `parallel: true` in its state model and `buildPayload()`.
It does not support the v3 fields: `index`, `phases`, or `preferred_workers`.
This is a feature gap, not a security issue — the backend still supports v2
format via backward compatibility.

### 3.4 Observations

| Item | Status | Notes |
|------|--------|-------|
| Inline `onclick` handlers | Acceptable | For a small project with no build step, inline handlers are pragmatic. A larger project should use `addEventListener`. |
| No form validation in editor | Minor gap | The editor does not validate that task names are non-empty or days > 0 on the client side before submission. The backend validates, so this is a UX issue, not a security issue. |
| `document.write()` in generateSchedule | Acceptable | Replaces the entire page with the server response. Works but less elegant than SPA-style DOM updates. Appropriate for this scope. |
| Editor doesn't support v3 features | Feature gap | Editor still generates v2-style payloads (no index, phases, preferred_workers). The backend accepts these fine via backward compat. |

---

## 4. Test Suite

### 4.1 Coverage — GOOD

| Test File             | Covers               | Count | Verdict |
|-----------------------|----------------------|-------|---------|
| `test_parser.py`      | YAML parsing (F1)    | 10    | Good    |
| `test_scheduler.py`   | LPT scheduling (F2)  | 7     | Good    |
| `test_colors.py`      | Color assignment (F7) | 6     | Good    |
| `test_web.py`         | Routes, rendering (F3-7, F13) | 16 | Good |
| `test_calendar.py`    | Calendar dates (F11)  | 6     | Good    |
| `test_dep_scheduler.py` | Dep scheduling (F9) | 8     | Good    |
| `test_dependencies.py`| Dep parsing (F8)      | 11    | Good    |
| `test_workers.py`     | Named workers (F10)   | 6     | Good    |
| `test_editor.py`      | Editor routes (F12)   | 9     | Good    |
| `test_indexing.py`    | Task indexing (F14)   | 16    | Good    |
| `test_phases.py`      | Phase hierarchy (F15) | 12    | Good    |
| `test_preferred.py`   | Preferred workers (F16) | 8   | Good    |
| **Total**             |                       | **115**| **All passing** |

### 4.2 Test Quality — GOOD

- Tests use descriptive names and docstrings explaining what is tested.
- Fixtures properly create isolated Flask test clients.
- Negative tests cover error conditions (missing fields, invalid values,
  circular dependencies, invalid indexes, empty phases).
- Edge cases tested: single task/worker, zero days, weekend starts, diamond
  dependency patterns, index gaps, cross-project phase deps, preferred worker
  with availability offsets.

### 4.3 Gaps & Recommendations

| Gap | Risk | Recommendation |
|-----|------|----------------|
| No test for oversized file upload (413) | Low | Flask's `MAX_CONTENT_LENGTH` handles this automatically. A test would confirm the behavior. |
| No test for duplicate task names in same project/phase | Low | Add a test verifying behavior when two tasks share a name (task_id collision). |
| No integration test for editor → schedule round-trip | Low | The editor submit test covers this partially. A fuller test could verify specific task positions in the rendered chart. |
| No test for malformed JSON to editor endpoints | Low | `get_json(silent=True)` returns `None` which triggers the 400 check. A test would confirm. |
| No test for invalid `preferred_workers` names | Low | Non-existent worker names in `preferred_workers` are silently ignored. A test documenting this behavior would be useful. |
| No CSS/JS tests | Acceptable | Given the pure server-side rendering approach, template content tests cover the HTML output adequately. |

---

## 5. Security Analysis

### 5.1 OWASP Top 10 Review

| Risk | Status | Details |
|------|--------|---------|
| **Broken Access Control (A01)** | N/A | No authentication or authorization system. The app is designed for local single-user use. |
| **Cryptographic Failures (A02)** | N/A | No secrets, passwords, or encryption involved. |
| **Injection (A03)** | Mitigated | See detailed analysis in §5.2. |
| **Insecure Design (A04)** | Mitigated | File uploads are processed in-memory only (never written to disk). `MAX_CONTENT_LENGTH` limits upload size to 1 MB. |
| **Security Misconfiguration (A05)** | **W1** | `debug=True` in `run.py` — exposes the Werkzeug interactive debugger which allows arbitrary code execution if the app is reachable on a network. See §5.3. |
| **Vulnerable Components (A06)** | Low risk | Minimal dependency footprint (Flask, PyYAML). Both are mature, actively maintained libraries. |
| **Authentication Failures (A07)** | N/A | No authentication system. |
| **Data Integrity Failures (A08)** | Mitigated | YAML parsing is validated thoroughly. Editor JSON round-trips through the same validation. |
| **Logging Failures (A09)** | Acceptable | Flask's built-in request logging covers development needs. Production deployment would benefit from structured logging. |
| **SSRF (A10)** | N/A | No outbound HTTP requests made by the server. |

### 5.2 Injection Analysis — PASS

**YAML Deserialization:**
- `yaml.safe_load()` is used exclusively — prevents arbitrary Python object
  construction via YAML tags (`!!python/object`, etc.). This is the correct
  defense against YAML deserialization attacks (CWE-502).

**Cross-Site Scripting (XSS) — Server-Side:**
- Jinja2 auto-escaping is enabled by default for `.html` templates. All
  user-controlled values (`{{ st.task.name }}`, `{{ st.task.project }}`,
  `{{ project }}`, `{{ worker_names[w].name }}`) are auto-escaped.
- Error messages use `markupsafe.escape()` before interpolation into
  response strings (`f"Invalid configuration: {escape(str(exc))}"`) in
  both the `/upload` and `/editor/submit` routes.) — correct.
- **Inline style attributes** in `schedule.html` use `{{ color }}` and
  `{{ st.task.days }}` in `style=""` attributes. The `color` values come
  from `ColorAssigner` (hardcoded hex and computed HSL strings, never from
  user input), and `days`/column numbers are integers — no injection vector.

**Cross-Site Scripting (XSS) — Client-Side:**
- Editor JS uses `esc()` function which encodes via `textContent` → `innerHTML`
  on a disposable `<div>`. This correctly escapes `<`, `>`, `&`, `"` etc.
- The `esc()` function is applied to all user-provided values rendered into
  the DOM: worker names, project names, task names, dependency tags, and
  `<option>` values.

**SQL Injection:**
- N/A — no database involved.

**Command Injection:**
- N/A — no `os.system()`, `subprocess`, or `eval()` calls anywhere.

### 5.3 Specific Findings

#### W1: `debug=True` Hardcoded in `run.py` — MEDIUM

**File:** `run.py`, line 14
**Risk:** The Werkzeug debugger allows interactive Python execution in the
browser if an exception occurs. If the dev server is bound to `0.0.0.0` or
exposed through port forwarding, any network-reachable user can execute
arbitrary code on the host machine. Even on `localhost`, other local
processes or browser exploits could abuse it.

**Current state:** The server binds to `localhost:5000` (Flask default), so
the risk is limited to local access. However, the debug mode also disables
some response caching and adds overhead.

**Recommendation:** Use an environment variable:
```python
app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", port=5000)
```

#### W2: No `workers` Upper Bound — LOW

**File:** `parser.py`, worker parsing section
**Risk:** A YAML config with `workers: 999999` would cause the scheduler to
allocate a list of 999,999 entries and iterate over them for every task.
Combined with a large task count, this could cause excessive memory use or
a hang.

**Current state:** The `MAX_CONTENT_LENGTH` of 1 MB limits the YAML payload
size, which practically caps the worker count (a 1 MB YAML can only describe
so many named workers). The risk of abuse is low.

**Recommendation:** Add an upper-bound check (e.g., `workers <= 1000`) in
the parser.

#### W3: No Task Count Upper Bound — LOW

**File:** `parser.py`, task parsing
**Risk:** The transitive closure computation (`_transitive_close`) has
O(n × d) complexity where d is the average dependency count per task.
For a pathological config with thousands of tasks in a deep chain, the
transitive closure could produce very large dependency lists and consume
significant memory.

**Current state:** Again limited by the 1 MB upload cap. A 1 MB YAML
file can describe at most a few thousand tasks, which is manageable.

**Recommendation:** Add a task count limit (e.g., 10,000) or a total
dependency-edge limit as a safeguard.

#### M1: Editor Downloads YAML Without Validation — LOW

**File:** `routes.py`, `/editor/download` endpoint
**Risk:** The `/editor/download` route calls `EditorService.json_to_yaml_string()`
which converts editor JSON to YAML without running it through `parse_config`.
This means a user can download a YAML file that may not pass validation
(e.g., missing days, empty project names).

**Current state:** This is a UX issue, not a security issue. The downloaded
file will simply fail when uploaded later. The endpoint checks for
`data.get("projects")` presence but does no deeper validation.

**Recommendation:** Either validate before download (call `json_to_config`
first) or accept the trade-off for download flexibility.

### 5.4 Input Validation Summary

| Input | Validation |
|-------|-----------|
| YAML file upload | Extension allowlist, 1 MB size limit, `safe_load`, full schema validation, circular dep detection |
| Editor JSON (submit) | `get_json(silent=True)` + `projects` presence check + full `parse_config` validation via round-trip |
| Editor JSON (download) | `get_json(silent=True)` + `projects` presence check only — no schema validation |
| File name | `os.path.splitext` + allowlist check; name is never used for file I/O |
| Task index format | Regex validation (`^(\d+)([A-Za-z]?)$`) |
| Dependency references | Validated against known task IDs and phase IDs |
| `preferred_workers` | Not validated against known worker names (silently ignored if unknown) |

### 5.5 Security Recommendations

| Item | Priority | Action |
|------|----------|--------|
| `debug=True` in production (W1) | Medium | Use `os.getenv("FLASK_DEBUG", "0") == "1"` |
| Worker count upper bound (W2) | Low | Add `workers <= 1000` check in parser |
| Task count upper bound (W3) | Low | Add task count limit or document expected input bounds |
| CSRF protection | Low | The app has no authentication so CSRF risk is minimal. If auth were added, Flask-WTF's CSRF tokens should be used for all POST forms. |
| Content-Security-Policy | Low | Adding a CSP header would harden against inline script injection. Currently not needed since there are no inline scripts (editor.js is external). The `style` attributes on task blocks use Jinja2 auto-escaping. |
| Rate limiting | Low | No rate limiting on upload or editor submit endpoints. Not needed for local use; add Flask-Limiter if deploying to a network. |
| Validate download before serving (M1) | Low | Run `json_to_config` in `/editor/download` to catch invalid configs early |

---

## 6. Performance Considerations

### 6.1 Scheduling Algorithm

- **Time complexity:** O(n log n) for the topological sort + O(n·k) for worker
  assignment where n = tasks, k = workers.
- **Space complexity:** O(n + k) base, plus O(n²) worst-case for transitive
  closure dependency lists (deep chain of n tasks).
- For typical use cases (tens to low hundreds of tasks, single-digit workers),
  this is negligible.

### 6.2 Transitive Closure

- The `_transitive_close()` function propagates dependency sets through the
  topological order. Worst case: a chain of n tasks produces dependency lists
  of sizes 0, 1, 2, ..., n-1, totaling O(n²) set entries.
- For the current `work_planning.yaml` (39 tasks), this is trivially fast.
- For very large configs (1000+ tasks), memory usage could be notable but
  is bounded by the 1 MB upload limit.

### 6.3 Template Rendering

- The Gantt chart is rendered entirely server-side with Jinja2. For very large
  schedules (1000+ days, hundreds of tasks), the HTML output could become very
  large. This is acceptable for the project's intended use case.

### 6.4 Static Assets

- CSS and JS files are small (< 10 KB each). No bundling or minification is
  needed at this scale.
- Flask's built-in static file serving is adequate for local development.
  A production deployment should use a reverse proxy (nginx) for static files.

---

## 7. Documentation

### 7.1 Code Documentation — GOOD

| File | Module docstring | Class docstrings | Function docstrings | Verdict |
|------|:---:|:---:|:---:|---------|
| `__init__.py` | Yes | — | Yes | Good |
| `models.py` | Yes | Yes (all 6) | — (dataclasses) | Good |
| `parser.py` | Yes | Yes | Yes (all methods) | Good |
| `scheduler.py` | Yes | Yes | Yes | Good |
| `colors.py` | Yes | Yes | Yes | Good |
| `calendar.py` | Yes | — | Yes | Good |
| `editor.py` | Yes | Yes | Yes (all 3 methods) | Good |
| `routes.py` | Yes | — | Yes (all 5) | Good |
| `run.py` | Yes | — | — | Good |
| `editor.js` | Yes | — | Yes (all) | Good |

### 7.2 Project Documentation — GOOD

| Document | Status | Notes |
|----------|--------|-------|
| `README.md` | Complete | Setup, usage, config format, project structure, routes, future features |
| `DESIGN.md` | Complete | Architecture, tech stack, all 16 features, v3 config format, directory structure |
| `PROGRESS.md` | Complete | TDD log for all 16 features + reorganization with test results |
| `AUDIT.md` | This document | Full project audit (revision 2) |

### 7.3 Documentation Accuracy

All file references in DESIGN.md and PROGRESS.md have been verified to match
the current codebase structure (using `backend/` module paths).

**Note:** The `editor.js` JSDoc still documents the v2 state model
(`parallel: boolean`) and does not mention v3 fields (`index`, `phases`,
`preferred_workers`). This is consistent with the editor not yet supporting
v3 features (see §3.3).

---

## 8. Dependency Health

| Package | Pinned Version | Latest Stable | Risk |
|---------|---------------|---------------|------|
| Flask   | >= 3.0        | 3.x           | Low — mature, actively maintained |
| PyYAML  | >= 6.0        | 6.x           | Low — widely used, stable API |
| pytest  | >= 8.0        | 8.x           | Low — dev dependency only |

**Transitive dependencies:** Flask pulls in Werkzeug, Jinja2, MarkupSafe,
click, itsdangerous, and blinker. All are maintained by the Pallets project.

**Recommendation:** Consider pinning exact versions in a `requirements.lock`
for reproducible builds, while keeping `requirements.txt` as the minimum
version specification.

---

## 9. Findings Summary

### Critical Issues

None.

### Warnings

| # | Area | Finding | Severity |
|---|------|---------|----------|
| W1 | Security | `debug=True` hardcoded in `run.py` — exposes Werkzeug debugger | Medium |
| W2 | Validation | No upper bound on worker count — pathological inputs could cause high memory use | Low |
| W3 | Validation | No upper bound on task count — transitive closure is O(n²) worst case | Low |

### Minor Observations

| # | Area | Finding | Severity |
|---|------|---------|----------|
| M1 | Validation | `/editor/download` serves YAML without running `parse_config` validation | Low |
| M2 | Validation | Duplicate task names within a project/phase are not detected (task_id collision) | Low |
| M3 | Validation | `preferred_workers` entries not validated against known worker names | Low |
| M4 | UX | Editor has no client-side validation before backend submission | Low |
| M5 | Feature | Editor JS does not support v3 features (index, phases, preferred_workers) | Low |
| M6 | Deployment | No production-ready configuration (WSGI server, CSP headers) | Low |

### Strengths

- Clean separation of concerns with single-purpose modules.
- Thorough TDD approach with 115 tests covering all 16 features.
- Secure input handling: `safe_load`, Jinja2 auto-escaping, `markupsafe.escape()`,
  `esc()` DOM encoding, in-memory file processing.
- Minimal dependency footprint with mature, well-maintained libraries.
- Comprehensive documentation: README, design doc, progress log, and this audit.
- Backward-compatible configuration format (v1, v2, and v3 all supported).
- No framework or build-tool dependencies on the frontend.
- Transitive dependency closure ensures correct scheduling even with complex
  dep chains.
- Preferred worker allocation never sacrifices makespan — sound algorithm design.

---

## Fix Plan

### Priority 1 — W1: `debug=True` (Medium)
**File:** `run.py`
**Change:** Replace `app.run(debug=True, port=5000)` with:
```python
import os
app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", port=5000)
```
Impact: Debugger is off by default. Set `FLASK_DEBUG=1` env var for dev mode.

### Priority 2 — W2 + W3: Input Bounds (Low)
**File:** `parser.py`
**Change:** Add upper-bound checks after worker/task parsing:
- `if workers_count > 1000: raise ValueError("Worker count exceeds maximum (1000)")`
- After collecting all tasks: `if len(tasks) > 10000: raise ValueError("Task count exceeds maximum (10,000)")`

### Priority 3 — M1: Validate Editor Download (Low)
**File:** `routes.py`, `/editor/download`
**Change:** Call `EditorService.json_to_config(data)` before generating YAML,
so invalid configs are rejected with a 400 rather than silently downloaded.

### Priority 4 — M3: Validate Preferred Workers (Low)
**File:** `parser.py`, after all tasks/workers are parsed
**Change:** Check that every `preferred_workers` entry matches a known worker
name, and raise `ValueError` if not.

---

*Awaiting feedback before implementing fixes.*
