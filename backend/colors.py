"""Project color assignment using a distinct color palette.

Assigns unique CSS color strings to project names for visual
differentiation in the Gantt chart.  Uses the Tableau 10 palette
for up to 12 projects, then generates evenly-spaced HSL colors.  
"""

from __future__ import annotations


class ColorAssigner:
    """Assigns unique, visually distinct colors to projects.

    Class Attributes:
        PALETTE: 12 hand-picked hex colors from the Tableau 10 + 2
            extra palette, chosen for mutual contrast and readability
            on white backgrounds.
    """

    PALETTE = [
        "#4e79a7", "#f28e2b", "#e15759", "#76b7b2",
        "#59a14f", "#edc948", "#b07aa1", "#ff9da7",
        "#9c755f", "#bab0ac", "#6b6ecf", "#d67195",
    ]

    @classmethod
    def assign(cls, project_names: list[str]) -> dict[str, str]:
        """Assign a unique color to each project name.

        Uses the predefined palette for the first 12 projects, then
        generates evenly-spaced HSL colors for additional projects.

        Args:
            project_names: Ordered list of project names.  Order
                determines palette assignment.

        Returns:
            Dict mapping each project name to a CSS color string
            (hex ``#rrggbb`` or ``hsl(h, s%, l%)``).
        """
        colors: dict[str, str] = {}
        for i, name in enumerate(project_names):
            if i < len(cls.PALETTE):
                colors[name] = cls.PALETTE[i]
            else:
                hue = int((360 / len(project_names)) * i) % 360
                colors[name] = f"hsl({hue}, 65%, 55%)"
        return colors


# Convenience alias for backward-compatible imports.
assign_project_colors = ColorAssigner.assign
