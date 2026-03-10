"""Work Scheduler backend package.

Provides the Flask application factory and re-exports core components
for convenient importing::

    from backend import create_app, parse_config, schedule_tasks

Modules:
    models      -- Dataclass definitions (Task, Config, Schedule, etc.)
    parser      -- YAML configuration parsing and validation
    scheduler   -- Dependency-aware task scheduling (topological sort + LPT)
    colors      -- Project color palette assignment
    calendar    -- Calendar date computation with weekend handling
    editor      -- JSON-to-YAML conversion for the graphical editor
    routes      -- Flask Blueprint with all HTTP route handlers
"""

from __future__ import annotations

import os

from flask import Flask

from .calendar import compute_calendar_dates
from .colors import ColorAssigner, assign_project_colors
from .editor import EditorService
from .models import (
    CalendarSettings,
    Config,
    Schedule,
    ScheduledTask,
    Task,
    WorkerInfo,
)
from .parser import ConfigParser, parse_config
from .routes import main_bp
from .scheduler import TaskScheduler, schedule_tasks

_MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB


def create_app() -> Flask:
    """Application factory for the Work Scheduler Flask app.

    Creates and configures a Flask instance with:
      - Template folder: ``assets/templates/``
      - Static folder: ``assets/`` (served at ``/assets``)
      - Upload limit: 1 MB
      - All routes registered via :data:`main_bp` Blueprint

    Returns:
        A fully configured Flask application ready to serve.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "assets", "templates"),
        static_folder=os.path.join(base_dir, "assets"),
        static_url_path="/assets",
    )
    app.config["MAX_CONTENT_LENGTH"] = _MAX_FILE_SIZE
    app.register_blueprint(main_bp)
    return app


__all__ = [
    "CalendarSettings",
    "ColorAssigner",
    "Config",
    "ConfigParser",
    "EditorService",
    "Schedule",
    "ScheduledTask",
    "Task",
    "TaskScheduler",
    "WorkerInfo",
    "assign_project_colors",
    "compute_calendar_dates",
    "create_app",
    "parse_config",
    "schedule_tasks",
]
