"""Tests for Feature 1: YAML Configuration Parsing

Tests that the YAML parser correctly reads configuration files,
validates required fields, and produces correct data models.
"""
import pytest
from backend import Task, Config, parse_config


VALID_YAML = """
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
"""


class TestParseConfig:
    """Tests for the parse_config function."""

    def test_parse_valid_config_returns_config(self):
        """A valid YAML string should produce a Config object."""
        config = parse_config(VALID_YAML)
        assert isinstance(config, Config)

    def test_parse_workers_count(self):
        """Workers count should match the YAML value."""
        config = parse_config(VALID_YAML)
        assert config.workers == 3

    def test_parse_flattens_tasks(self):
        """Tasks from all projects should be flattened into a single list."""
        config = parse_config(VALID_YAML)
        assert len(config.tasks) == 3

    def test_task_has_project_name(self):
        """Each task should carry its parent project name."""
        config = parse_config(VALID_YAML)
        api_tasks = [t for t in config.tasks if t.project == "Backend API"]
        assert len(api_tasks) == 2

    def test_task_fields(self):
        """Each task should have name, days, and project fields."""
        config = parse_config(VALID_YAML)
        task = config.tasks[0]
        assert isinstance(task, Task)
        assert isinstance(task.name, str)
        assert isinstance(task.days, int)
        assert isinstance(task.project, str)

    def test_parse_missing_workers_raises(self):
        """Missing 'workers' field should raise ValueError."""
        bad_yaml = """
projects:
  - name: "Test"
    tasks:
      - name: "Task1"
        days: 1
"""
        with pytest.raises(ValueError, match="workers"):
            parse_config(bad_yaml)

    def test_parse_zero_workers_raises(self):
        """Zero workers should raise ValueError."""
        bad_yaml = """
workers: 0
projects:
  - name: "Test"
    tasks:
      - name: "Task1"
        days: 1
"""
        with pytest.raises(ValueError, match="workers"):
            parse_config(bad_yaml)

    def test_parse_missing_projects_raises(self):
        """Missing 'projects' field should raise ValueError."""
        bad_yaml = "workers: 2\n"
        with pytest.raises(ValueError, match="projects"):
            parse_config(bad_yaml)

    def test_parse_task_missing_days_raises(self):
        """Task without 'days' should raise ValueError."""
        bad_yaml = """
workers: 1
projects:
  - name: "Test"
    tasks:
      - name: "No days"
"""
        with pytest.raises(ValueError, match="days"):
            parse_config(bad_yaml)

    def test_parse_negative_days_raises(self):
        """Negative days should raise ValueError."""
        bad_yaml = """
workers: 1
projects:
  - name: "Test"
    tasks:
      - name: "Bad task"
        days: -1
"""
        with pytest.raises(ValueError, match="days"):
            parse_config(bad_yaml)
