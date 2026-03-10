"""Tests for Feature 8: Task Dependencies — Config & Parsing

Tests that the parser handles sequential-by-default tasks, parallel: true,
cross-project depends_on, and validates dependency references.
"""
import pytest
from backend import Task, Config, parse_config


# --- Sequential by default ---

SEQUENTIAL_YAML = """
workers: 2
projects:
  - name: "P1"
    tasks:
      - name: "A"
        days: 2
      - name: "B"
        days: 3
      - name: "C"
        days: 1
"""


class TestSequentialByDefault:
    """Tasks within a project are sequential unless marked parallel."""

    def test_second_task_depends_on_first(self):
        config = parse_config(SEQUENTIAL_YAML)
        task_b = next(t for t in config.tasks if t.name == "B")
        assert "P1/A" in task_b.depends_on

    def test_third_task_depends_on_second(self):
        config = parse_config(SEQUENTIAL_YAML)
        task_c = next(t for t in config.tasks if t.name == "C")
        assert "P1/B" in task_c.depends_on

    def test_first_task_has_no_dependencies(self):
        config = parse_config(SEQUENTIAL_YAML)
        task_a = next(t for t in config.tasks if t.name == "A")
        assert task_a.depends_on == []

    def test_task_id_format(self):
        config = parse_config(SEQUENTIAL_YAML)
        task_a = next(t for t in config.tasks if t.name == "A")
        assert task_a.task_id == "P1/A"


# --- Parallel opt-in ---

PARALLEL_YAML = """
workers: 2
projects:
  - name: "P1"
    tasks:
      - name: "A"
        days: 2
      - name: "B"
        days: 3
      - name: "C"
        parallel: true
        days: 1
"""


class TestParallelOptIn:
    """parallel: true removes the implicit dependency on predecessor."""

    def test_parallel_task_does_not_depend_on_predecessor(self):
        config = parse_config(PARALLEL_YAML)
        task_c = next(t for t in config.tasks if t.name == "C")
        assert "P1/B" not in task_c.depends_on

    def test_parallel_task_inherits_predecessor_deps(self):
        """C (parallel) should depend on A, same as B does."""
        config = parse_config(PARALLEL_YAML)
        task_c = next(t for t in config.tasks if t.name == "C")
        assert "P1/A" in task_c.depends_on

    def test_first_task_parallel_has_no_deps(self):
        """parallel: true on the first task = no deps (nothing to inherit)."""
        yaml_str = """
workers: 1
projects:
  - name: "P1"
    tasks:
      - name: "A"
        parallel: true
        days: 2
"""
        config = parse_config(yaml_str)
        task_a = next(t for t in config.tasks if t.name == "A")
        assert task_a.depends_on == []


# --- Cross-project depends_on ---

CROSS_YAML = """
workers: 2
projects:
  - name: "Backend"
    tasks:
      - name: "API"
        days: 3
  - name: "Frontend"
    tasks:
      - name: "UI"
        days: 2
        depends_on:
          - "Backend/API"
"""


class TestCrossProjectDependency:
    """Cross-project depends_on adds to dependencies."""

    def test_cross_project_dependency_present(self):
        config = parse_config(CROSS_YAML)
        task_ui = next(t for t in config.tasks if t.name == "UI")
        assert "Backend/API" in task_ui.depends_on

    def test_combined_implicit_and_explicit_deps(self):
        yaml_str = """
workers: 2
projects:
  - name: "Backend"
    tasks:
      - name: "API"
        days: 3
  - name: "Frontend"
    tasks:
      - name: "Design"
        days: 1
      - name: "UI"
        days: 2
        depends_on:
          - "Backend/API"
"""
        config = parse_config(yaml_str)
        task_ui = next(t for t in config.tasks if t.name == "UI")
        assert "Frontend/Design" in task_ui.depends_on
        assert "Backend/API" in task_ui.depends_on


# --- Validation ---

class TestDependencyValidation:
    """Invalid dependency references must raise errors."""

    def test_invalid_dependency_ref_raises(self):
        yaml_str = """
workers: 1
projects:
  - name: "P1"
    tasks:
      - name: "A"
        days: 2
        depends_on:
          - "NonExistent/Task"
"""
        with pytest.raises(ValueError, match="dependency"):
            parse_config(yaml_str)

    def test_circular_dependency_raises(self):
        yaml_str = """
workers: 1
projects:
  - name: "P1"
    tasks:
      - name: "A"
        days: 2
        depends_on:
          - "P1/B"
      - name: "B"
        parallel: true
        days: 1
        depends_on:
          - "P1/A"
"""
        with pytest.raises(ValueError, match="[Cc]ircular"):
            parse_config(yaml_str)
