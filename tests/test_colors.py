"""Tests for Feature 7: Project Color Assignment

Tests that each project receives a unique, consistent color.
"""
import pytest
from backend import assign_project_colors


class TestAssignProjectColors:
    """Tests for the assign_project_colors function."""

    def test_returns_dict(self):
        """Should return a dict mapping project names to color strings."""
        colors = assign_project_colors(["Project A", "Project B"])
        assert isinstance(colors, dict)

    def test_unique_colors_per_project(self):
        """Each project should get a unique color."""
        projects = ["Alpha", "Beta", "Gamma"]
        colors = assign_project_colors(projects)
        color_values = list(colors.values())
        assert len(set(color_values)) == len(projects)

    def test_all_projects_have_colors(self):
        """Every project name must appear in the output dict."""
        projects = ["A", "B", "C"]
        colors = assign_project_colors(projects)
        for p in projects:
            assert p in colors

    def test_color_format_is_valid(self):
        """Colors should be valid CSS color strings (hex or hsl)."""
        colors = assign_project_colors(["P1"])
        color = colors["P1"]
        assert color.startswith("#") or color.startswith("hsl")

    def test_many_projects_still_unique(self):
        """Even with >12 projects, colors should still be unique."""
        projects = [f"Project_{i}" for i in range(20)]
        colors = assign_project_colors(projects)
        color_values = list(colors.values())
        assert len(set(color_values)) == 20

    def test_single_project(self):
        """Edge case: single project."""
        colors = assign_project_colors(["Solo"])
        assert "Solo" in colors
