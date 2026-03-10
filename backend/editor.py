"""Editor JSON-to-YAML conversion helpers.

Converts the JSON payload produced by the graphical config editor
into either a YAML string (for download) or a validated Config
object (for immediate scheduling).  Round-trips through YAML +
parse_config to reuse the battle-tested validation logic.
"""

from __future__ import annotations

import yaml

from .models import Config
from .parser import parse_config


class EditorService:
    """Converts editor JSON payloads to YAML and Config objects."""

    @staticmethod
    def json_to_yaml_string(data: dict) -> str:
        """Convert editor JSON payload to a YAML string for download.

        Produces a clean YAML document with only the fields relevant
        to the scheduler: worker names/count, calendar settings, and
        projects with their tasks (including parallel and depends_on).

        Args:
            data: The raw JSON object from the editor frontend.

        Returns:
            A YAML-formatted string suitable for saving as a config file.
        """
        out: dict = {}
        if data.get("worker_names"):
            out["worker_names"] = []
            for w in data["worker_names"]:
                entry: dict = {"name": w["name"]}
                avail = w.get("available_in", 0)
                if avail:
                    entry["available_in"] = avail
                out["worker_names"].append(entry)
        elif data.get("workers"):
            out["workers"] = data["workers"]

        if data.get("calendar"):
            out["calendar"] = {}
            if data["calendar"].get("start_date"):
                out["calendar"]["start_date"] = data["calendar"]["start_date"]
            if "show_weekends" in data["calendar"]:
                out["calendar"]["show_weekends"] = data["calendar"][
                    "show_weekends"
                ]

        out["projects"] = []
        for proj in data.get("projects", []):
            p: dict = {"name": proj["name"], "tasks": []}
            for t in proj.get("tasks", []):
                task_entry: dict = {"name": t["name"], "days": t["days"]}
                if t.get("parallel"):
                    task_entry["parallel"] = True
                if t.get("depends_on"):
                    task_entry["depends_on"] = t["depends_on"]
                p["tasks"].append(task_entry)
            out["projects"].append(p)

        return yaml.dump(out, default_flow_style=False, sort_keys=False)

    @staticmethod
    def json_to_config(data: dict) -> Config:
        """Convert editor JSON payload to a validated Config object.

        Round-trips through ``json_to_yaml_string`` then ``parse_config``
        to reuse all existing parsing and validation logic.

        Args:
            data: The raw JSON object from the editor frontend.

        Returns:
            A fully validated Config ready for scheduling.

        Raises:
            ValueError: If the configuration is invalid.
            yaml.YAMLError: If the intermediate YAML is malformed.
        """
        yaml_str = EditorService.json_to_yaml_string(data)
        return parse_config(yaml_str)
