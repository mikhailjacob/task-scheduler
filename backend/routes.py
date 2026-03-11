"""Flask route handlers for the Work Scheduler application.

Defines a Flask Blueprint (``main_bp``) with routes for:

- ``GET /``                -- Landing page (upload form + editor link)
- ``POST /upload``         -- File upload to schedule rendering
- ``GET /editor``          -- Graphical config editor page
- ``POST /editor/submit``  -- Editor JSON to schedule rendering
- ``POST /editor/download``-- Editor JSON to YAML file download
"""

from __future__ import annotations

import os

import yaml
from flask import Blueprint, Response, render_template, request
from markupsafe import escape

from .calendar import compute_calendar_dates
from .colors import assign_project_colors
from .editor import EditorService
from .models import CalendarSettings, Config
from .parser import parse_config
from .scheduler import schedule_tasks

ALLOWED_EXTENSIONS = {".yaml", ".yml"}
"""File extensions accepted by the upload endpoint."""

main_bp = Blueprint("main", __name__)


def _build_schedule_context(config: Config) -> dict:
    """Schedule tasks and prepare template context variables.

    Runs the scheduler, assigns project colors, computes calendar
    dates, and packages everything into a dict for Jinja2 template
    rendering.

    Args:
        config: A validated Config object.

    Returns:
        Dict with keys: ``schedule``, ``colors``, ``total_days``,
        ``num_workers``, ``worker_names``, ``calendar_dates``,
        ``show_calendar``, ``show_weekends``.
    """
    schedule = schedule_tasks(config)
    project_names = list(dict.fromkeys(t.project for t in config.tasks))
    colors = assign_project_colors(project_names)
    cal = config.calendar or CalendarSettings()
    dates = compute_calendar_dates(cal, schedule.total_days)
    return dict(
        schedule=schedule,
        colors=colors,
        total_days=schedule.total_days,
        num_workers=config.workers,
        worker_names=schedule.worker_names,
        calendar_dates=dates,
        show_calendar=True,
        show_weekends=cal.show_weekends,
    )


@main_bp.route("/")
def index():
    """Render the landing page with upload form and editor link."""
    return render_template("index.html")


@main_bp.route("/upload", methods=["POST"])
def upload():
    """Handle YAML file upload, parse, schedule, and render chart.

    Validates the uploaded file (presence, extension, content), parses
    the YAML into a Config, schedules the tasks, and returns the
    rendered Gantt chart page.

    Returns:
        Tuple of (rendered HTML, 200) on success, or
        (error message, 400) on validation/parsing failure.
    """
    if "file" not in request.files:
        return "No file uploaded", 400
    file = request.files["file"]
    if not file.filename:
        return "No file selected", 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return "Only .yaml / .yml files are accepted", 400

    raw = file.read()
    try:
        config = parse_config(raw.decode("utf-8"))
    except (ValueError, yaml.YAMLError) as exc:
        return f"Invalid configuration: {escape(str(exc))}", 400

    ctx = _build_schedule_context(config)
    return render_template("schedule.html", **ctx)


@main_bp.route("/editor")
def editor():
    """Render the graphical configuration editor page."""
    return render_template("editor.html")


@main_bp.route("/editor/submit", methods=["POST"])
def editor_submit():
    """Accept editor JSON, schedule tasks, and return the Gantt chart.

    Expects a JSON body with ``projects``, ``worker_names``, and
    optional ``calendar`` fields.  Returns rendered schedule HTML.

    Returns:
        Tuple of (rendered HTML, 200) on success, or
        (error message, 400) on invalid/empty configuration.
    """
    data = request.get_json(silent=True)
    if not data or not data.get("projects"):
        return "Invalid or empty configuration", 400
    try:
        config = EditorService.json_to_config(data)
    except (ValueError, yaml.YAMLError) as exc:
        return f"Invalid configuration: {escape(str(exc))}", 400
    ctx = _build_schedule_context(config)
    return render_template("schedule.html", **ctx)


@main_bp.route("/editor/download", methods=["POST"])
def editor_download():
    """Accept editor JSON and return a downloadable YAML config file.

    Expects the same JSON body as ``/editor/submit``.  Returns a
    ``config.yaml`` attachment with ``text/yaml`` content type.

    Returns:
        YAML file response with attachment header on success, or
        (error message, 400) on invalid/empty configuration.
    """
    data = request.get_json(silent=True)
    if not data or not data.get("projects"):
        return "Invalid or empty configuration", 400
    try:
        EditorService.json_to_config(data)
    except (ValueError, yaml.YAMLError) as exc:
        return f"Invalid configuration: {escape(str(exc))}", 400
    yaml_str = EditorService.json_to_yaml_string(data)
    return Response(
        yaml_str,
        mimetype="text/yaml",
        headers={
            "Content-Disposition": "attachment; filename=config.yaml"
        },
    )
