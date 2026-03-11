"""Tests for Feature 15: Phase Hierarchy."""

import pytest

from backend.parser import parse_config
from backend.scheduler import TaskScheduler


# ---------------------------------------------------------------------------
# Phase parsing basics
# ---------------------------------------------------------------------------

class TestPhaseParsing:
    """Projects can contain phases, each with their own tasks."""

    PHASED_CFG = """\
workers: 2
projects:
  - name: WebApp
    phases:
      - name: Design
        tasks:
          - name: Wireframes
            days: 3
            index: 1
          - name: Mockups
            days: 2
            index: 2
      - name: Build
        tasks:
          - name: Frontend
            days: 5
            index: 1
          - name: Backend
            days: 4
            index: 1
"""

    def test_task_id_includes_phase(self):
        cfg = parse_config(self.PHASED_CFG)
        ids = {t.task_id for t in cfg.tasks}
        assert "WebApp/Design/Wireframes" in ids
        assert "WebApp/Design/Mockups" in ids
        assert "WebApp/Build/Frontend" in ids
        assert "WebApp/Build/Backend" in ids

    def test_all_tasks_parsed(self):
        cfg = parse_config(self.PHASED_CFG)
        assert len(cfg.tasks) == 4

    def test_intra_phase_sequential_deps(self):
        cfg = parse_config(self.PHASED_CFG)
        by_id = {t.task_id: t for t in cfg.tasks}
        # Index 2 in Design depends on index 1 in Design
        assert "WebApp/Design/Wireframes" in by_id[
            "WebApp/Design/Mockups"
        ].depends_on

    def test_cross_phase_tasks_independent_by_default(self):
        cfg = parse_config(self.PHASED_CFG)
        by_id = {t.task_id: t for t in cfg.tasks}
        # Build/Frontend has no cross-phase dep unless explicit
        fe_deps = by_id["WebApp/Build/Frontend"].depends_on
        assert "WebApp/Design/Wireframes" not in fe_deps
        assert "WebApp/Design/Mockups" not in fe_deps


# ---------------------------------------------------------------------------
# Phase-level dependencies
# ---------------------------------------------------------------------------

class TestPhaseLevelDependency:
    """A task can depend on an entire phase (all tasks in it)."""

    CFG = """\
workers: 2
projects:
  - name: App
    phases:
      - name: Research
        tasks:
          - name: Survey
            days: 2
            index: 1
          - name: Analysis
            days: 3
            index: 1
      - name: Dev
        tasks:
          - name: Code
            days: 5
            index: 1
            depends_on:
              - App/Research
"""

    def test_phase_dep_expands_to_all_tasks(self):
        cfg = parse_config(self.CFG)
        by_id = {t.task_id: t for t in cfg.tasks}
        code_deps = by_id["App/Dev/Code"].depends_on
        assert "App/Research/Survey" in code_deps
        assert "App/Research/Analysis" in code_deps

    def test_schedule_respects_phase_dep(self):
        cfg = parse_config(self.CFG)
        sched = TaskScheduler.schedule(cfg)
        by_name = {st.task.name: st for st in sched.assignments}
        # Code cannot start before both Survey and Analysis are done
        research_end = max(
            by_name["Survey"].end_day,
            by_name["Analysis"].end_day,
        )
        assert by_name["Code"].start_day >= research_end


# ---------------------------------------------------------------------------
# Mixed projects: some with phases, some flat
# ---------------------------------------------------------------------------

class TestMixedProjects:
    """Projects can freely mix phased and flat styles."""

    CFG = """\
workers: 2
projects:
  - name: Phased
    phases:
      - name: P1
        tasks:
          - name: T1
            days: 2
            index: 1
  - name: Flat
    tasks:
      - name: F1
        days: 3
        index: 1
"""

    def test_phased_and_flat_coexist(self):
        cfg = parse_config(self.CFG)
        ids = {t.task_id for t in cfg.tasks}
        assert "Phased/P1/T1" in ids
        assert "Flat/F1" in ids

    def test_flat_task_can_depend_on_phased(self):
        yaml_str = """\
workers: 1
projects:
  - name: Phased
    phases:
      - name: P1
        tasks:
          - name: T1
            days: 2
            index: 1
  - name: Flat
    tasks:
      - name: F1
        days: 1
        index: 1
        depends_on:
          - Phased/P1/T1
"""
        cfg = parse_config(yaml_str)
        by_id = {t.task_id: t for t in cfg.tasks}
        assert "Phased/P1/T1" in by_id["Flat/F1"].depends_on


# ---------------------------------------------------------------------------
# Phase validation errors
# ---------------------------------------------------------------------------

class TestPhaseValidation:
    """Bad phase definitions produce clear errors."""

    def test_empty_phase_tasks_raises(self):
        yaml_str = """\
workers: 1
projects:
  - name: P
    phases:
      - name: Empty
        tasks: []
"""
        with pytest.raises(ValueError, match="non-empty"):
            parse_config(yaml_str)

    def test_phase_missing_name_raises(self):
        yaml_str = """\
workers: 1
projects:
  - name: P
    phases:
      - tasks:
          - name: T
            days: 1
            index: 1
"""
        with pytest.raises(ValueError, match="must have a 'name'"):
            parse_config(yaml_str)

    def test_invalid_phase_dep_reference_raises(self):
        yaml_str = """\
workers: 1
projects:
  - name: P
    phases:
      - name: A
        tasks:
          - name: T
            days: 1
            index: 1
            depends_on:
              - P/NonExistent
"""
        with pytest.raises(ValueError, match="not found"):
            parse_config(yaml_str)


# ---------------------------------------------------------------------------
# Cross-project phase dependency
# ---------------------------------------------------------------------------

class TestCrossProjectPhaseDep:
    """Phase deps can span projects."""

    CFG = """\
workers: 2
projects:
  - name: Infra
    phases:
      - name: Setup
        tasks:
          - name: Provision
            days: 2
            index: 1
          - name: Configure
            days: 1
            index: 2
  - name: App
    phases:
      - name: Dev
        tasks:
          - name: Code
            days: 3
            index: 1
            depends_on:
              - Infra/Setup
"""

    def test_cross_project_phase_dep_expanded(self):
        cfg = parse_config(self.CFG)
        by_id = {t.task_id: t for t in cfg.tasks}
        code_deps = by_id["App/Dev/Code"].depends_on
        assert "Infra/Setup/Provision" in code_deps
        assert "Infra/Setup/Configure" in code_deps
