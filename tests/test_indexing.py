"""Tests for Feature 14: Task Indexing & Transitive Dependencies."""

import pytest

from backend.parser import parse_config
from backend.scheduler import TaskScheduler


# ---------------------------------------------------------------------------
# Index parsing and validation
# ---------------------------------------------------------------------------

class TestIndexParsing:
    """Verify that indexed tasks are correctly parsed."""

    BASIC_INDEXED = """\
workers: 2
projects:
  - name: Alpha
    tasks:
      - name: Setup
        days: 2
        index: 1
      - name: Build
        days: 3
        index: 2
"""

    def test_index_stored_on_task(self):
        cfg = parse_config(self.BASIC_INDEXED)
        by_name = {t.name: t for t in cfg.tasks}
        assert by_name["Setup"].index == "1"
        assert by_name["Build"].index == "2"

    def test_sequential_indexes_create_dependency(self):
        cfg = parse_config(self.BASIC_INDEXED)
        by_name = {t.name: t for t in cfg.tasks}
        assert "Alpha/Setup" in by_name["Build"].depends_on

    def test_first_index_has_no_deps(self):
        cfg = parse_config(self.BASIC_INDEXED)
        by_name = {t.name: t for t in cfg.tasks}
        assert by_name["Setup"].depends_on == []

    def test_task_id_format(self):
        cfg = parse_config(self.BASIC_INDEXED)
        ids = {t.task_id for t in cfg.tasks}
        assert ids == {"Alpha/Setup", "Alpha/Build"}


class TestInvalidIndex:
    """Invalid index formats are rejected."""

    def test_non_alphanumeric_index_raises(self):
        yaml_str = """\
workers: 1
projects:
  - name: P
    tasks:
      - name: T
        days: 1
        index: "1-A"
"""
        with pytest.raises(ValueError, match="invalid index"):
            parse_config(yaml_str)

    def test_letter_only_index_raises(self):
        yaml_str = """\
workers: 1
projects:
  - name: P
    tasks:
      - name: T
        days: 1
        index: "A"
"""
        with pytest.raises(ValueError, match="invalid index"):
            parse_config(yaml_str)


# ---------------------------------------------------------------------------
# Parallel siblings (same number, different letter)
# ---------------------------------------------------------------------------

class TestParallelSiblings:
    """Tasks with same number but different letters are parallel."""

    PARALLEL_CFG = """\
workers: 3
projects:
  - name: Alpha
    tasks:
      - name: First
        days: 2
        index: 1
      - name: BranchA
        days: 3
        index: 2A
      - name: BranchB
        days: 4
        index: 2B
      - name: Merge
        days: 1
        index: 3
"""

    def test_parallel_siblings_share_predecessor_deps(self):
        cfg = parse_config(self.PARALLEL_CFG)
        by_name = {t.name: t for t in cfg.tasks}
        # Both 2A and 2B depend on index 1 (First)
        assert "Alpha/First" in by_name["BranchA"].depends_on
        assert "Alpha/First" in by_name["BranchB"].depends_on

    def test_parallel_siblings_do_not_depend_on_each_other(self):
        cfg = parse_config(self.PARALLEL_CFG)
        by_name = {t.name: t for t in cfg.tasks}
        assert "Alpha/BranchB" not in by_name["BranchA"].depends_on
        assert "Alpha/BranchA" not in by_name["BranchB"].depends_on

    def test_successor_depends_on_all_parallel_siblings(self):
        cfg = parse_config(self.PARALLEL_CFG)
        by_name = {t.name: t for t in cfg.tasks}
        assert "Alpha/BranchA" in by_name["Merge"].depends_on
        assert "Alpha/BranchB" in by_name["Merge"].depends_on

    def test_parallel_siblings_can_overlap_in_schedule(self):
        cfg = parse_config(self.PARALLEL_CFG)
        sched = TaskScheduler.schedule(cfg)
        by_name = {st.task.name: st for st in sched.assignments}
        # BranchA and BranchB can start at the same time
        assert by_name["BranchA"].start_day == by_name["BranchB"].start_day


# ---------------------------------------------------------------------------
# Transitive dependency closure
# ---------------------------------------------------------------------------

class TestTransitiveDependencies:
    """Verify that transitive closure inherits all ancestors."""

    CHAIN_CFG = """\
workers: 1
projects:
  - name: P
    tasks:
      - name: A
        days: 1
        index: 1
      - name: B
        days: 1
        index: 2
      - name: C
        days: 1
        index: 3
"""

    def test_transitive_closure_on_chain(self):
        cfg = parse_config(self.CHAIN_CFG)
        by_name = {t.name: t for t in cfg.tasks}
        # C directly depends on B (index 2), transitively on A (index 1)
        assert "P/A" in by_name["C"].depends_on
        assert "P/B" in by_name["C"].depends_on

    def test_middle_task_has_direct_dep_only(self):
        cfg = parse_config(self.CHAIN_CFG)
        by_name = {t.name: t for t in cfg.tasks}
        assert by_name["B"].depends_on == ["P/A"]


class TestTransitiveWithExplicitDeps:
    """Transitive closure with explicit cross-project deps."""

    CFG = """\
workers: 2
projects:
  - name: P1
    tasks:
      - name: X
        days: 2
        index: 1
      - name: Y
        days: 3
        index: 2
  - name: P2
    tasks:
      - name: Z
        days: 1
        index: 1
        depends_on:
          - P1/Y
"""

    def test_cross_project_explicit_dep_inherited(self):
        cfg = parse_config(self.CFG)
        by_name = {t.name: t for t in cfg.tasks}
        # Z depends on P1/Y explicitly, and transitively on P1/X
        assert "P1/Y" in by_name["Z"].depends_on
        assert "P1/X" in by_name["Z"].depends_on


# ---------------------------------------------------------------------------
# No implicit ordering from index numbers across projects
# ---------------------------------------------------------------------------

class TestNoImplicitCrossOrdering:
    """Index numbers only create deps within the same project/phase."""

    CFG = """\
workers: 2
projects:
  - name: Alpha
    tasks:
      - name: A1
        days: 2
        index: 1
  - name: Beta
    tasks:
      - name: B1
        days: 2
        index: 1
"""

    def test_same_index_different_projects_are_independent(self):
        cfg = parse_config(self.CFG)
        by_name = {t.name: t for t in cfg.tasks}
        assert by_name["A1"].depends_on == []
        assert by_name["B1"].depends_on == []

    def test_independent_tasks_can_be_scheduled_in_parallel(self):
        cfg = parse_config(self.CFG)
        sched = TaskScheduler.schedule(cfg)
        by_name = {st.task.name: st for st in sched.assignments}
        # With 2 workers, both can start at day 0
        assert by_name["A1"].start_day == 0
        assert by_name["B1"].start_day == 0


# ---------------------------------------------------------------------------
# Gap in index numbers
# ---------------------------------------------------------------------------

class TestIndexGaps:
    """Non-consecutive index numbers: only N-1 creates implicit dep."""

    CFG = """\
workers: 1
projects:
  - name: P
    tasks:
      - name: A
        days: 1
        index: 1
      - name: B
        days: 1
        index: 5
"""

    def test_gap_means_no_implicit_dep(self):
        """Index 5 does NOT implicitly depend on index 1 (only on index 4)."""
        cfg = parse_config(self.CFG)
        by_name = {t.name: t for t in cfg.tasks}
        # B is index 5, it only auto-depends on index 4 (which doesn't exist)
        assert by_name["B"].depends_on == []
