"""SVG export for the Gantt chart schedule.

Generates a standalone SVG image from a validated Config, replicating
the HTML Gantt chart layout with worker labels, day headers, colored
task blocks, and a project legend.
"""

from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, tostring

from .calendar import compute_calendar_dates
from .colors import assign_project_colors
from .models import CalendarSettings, Config
from .scheduler import schedule_tasks

# Layout constants (SVG user units ≈ pixels at 96 DPI).
_LABEL_W = 140
_COL_W = 50
_ROW_H = 40
_HEADER_H = 36
_LEGEND_H = 30
_PAD = 4
_FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"


def generate_schedule_svg(config: Config) -> str:
    """Generate a standalone SVG image of the Gantt chart.

    The SVG replicates the HTML schedule layout with worker rows,
    day-header columns, colored task blocks, and a project legend.

    Args:
        config: A validated ``Config`` object.

    Returns:
        A complete SVG document as a UTF-8 string, suitable for
        saving to a ``.svg`` file.
    """
    schedule = schedule_tasks(config)
    projects = list(dict.fromkeys(t.project for t in config.tasks))
    colors = assign_project_colors(projects)
    cal = config.calendar or CalendarSettings()
    dates = compute_calendar_dates(cal, schedule.total_days)

    td = schedule.total_days or 1
    nw = config.workers
    wn = schedule.worker_names

    width = _LABEL_W + td * _COL_W
    height = _LEGEND_H + _HEADER_H + nw * _ROW_H

    svg = Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "width": str(width),
        "height": str(height),
        "viewBox": f"0 0 {width} {height}",
    })

    # White background
    SubElement(svg, "rect", {
        "width": str(width), "height": str(height), "fill": "white",
    })

    # ---- Legend ----
    lx = _LABEL_W
    for proj, color in colors.items():
        SubElement(svg, "rect", {
            "x": str(lx), "y": "7", "width": "14", "height": "14",
            "rx": "3", "fill": color,
        })
        t = SubElement(svg, "text", {
            "x": str(lx + 20), "y": "18",
            "font-family": _FONT, "font-size": "12", "fill": "#444",
        })
        t.text = proj
        lx += max(len(proj) * 8, 40) + 36

    # ---- Day headers ----
    for d in range(schedule.total_days):
        cx = _LABEL_W + d * _COL_W + _COL_W // 2
        if dates and d < len(dates):
            _text(svg, cx, _LEGEND_H + 12, dates[d].strftime("%a"))
            _text(svg, cx, _LEGEND_H + 24, dates[d].strftime("%b %d"))
        else:
            _text(svg, cx, _LEGEND_H + 20, f"Day {d + 1}")

    # Header bottom rule
    SubElement(svg, "line", {
        "x1": "0", "y1": str(_LEGEND_H + _HEADER_H),
        "x2": str(width), "y2": str(_LEGEND_H + _HEADER_H),
        "stroke": "#eee",
    })

    # ---- Worker rows ----
    y0 = _LEGEND_H + _HEADER_H
    for w in range(nw):
        ry = y0 + w * _ROW_H

        # Worker label (right-aligned before the chart area)
        lbl = SubElement(svg, "text", {
            "x": str(_LABEL_W - 8), "y": str(ry + _ROW_H // 2 + 5),
            "text-anchor": "end", "font-family": _FONT,
            "font-size": "13", "font-weight": "600", "fill": "#555",
        })
        lbl.text = wn[w].name

        # Row bottom border
        SubElement(svg, "line", {
            "x1": "0", "y1": str(ry + _ROW_H),
            "x2": str(width), "y2": str(ry + _ROW_H),
            "stroke": "#f0f0f0",
        })

        # Availability offset block
        if wn[w].available_in > 0:
            bw = wn[w].available_in * _COL_W - 2
            SubElement(svg, "rect", {
                "x": str(_LABEL_W), "y": str(ry + _PAD),
                "width": str(bw), "height": str(_ROW_H - 2 * _PAD),
                "rx": "4", "fill": "#e0e0e0",
            })
            _text(svg, _LABEL_W + bw // 2, ry + _ROW_H // 2 + 4,
                  "Current Tasks", fill="#666")

        # Task blocks
        tasks = sorted(
            (a for a in schedule.assignments if a.worker == w),
            key=lambda a: a.start_day,
        )
        for st in tasks:
            bx = _LABEL_W + st.start_day * _COL_W
            bw = st.task.days * _COL_W - 2
            by = ry + _PAD
            bh = _ROW_H - 2 * _PAD
            color = colors.get(st.task.project, "#4e79a7")

            SubElement(svg, "rect", {
                "x": str(bx), "y": str(by), "width": str(bw),
                "height": str(bh), "rx": "4", "fill": color,
            })

            # Clip text to block bounds
            cid = f"c{w}-{st.start_day}"
            clip = SubElement(svg, "clipPath", {"id": cid})
            SubElement(clip, "rect", {
                "x": str(bx + 4), "y": str(by),
                "width": str(max(bw - 8, 0)), "height": str(bh),
            })

            txt = SubElement(svg, "text", {
                "x": str(bx + bw // 2), "y": str(by + bh // 2 + 4),
                "text-anchor": "middle", "font-family": _FONT,
                "font-size": "11", "font-weight": "500", "fill": "white",
                "clip-path": f"url(#{cid})",
            })
            txt.text = st.task.name

    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            + tostring(svg, encoding="unicode"))


def _text(parent: Element, x: int, y: int, content: str, *,
          size: str = "10", fill: str = "#999") -> Element:
    """Add a centered text element to *parent*."""
    el = SubElement(parent, "text", {
        "x": str(x), "y": str(y), "text-anchor": "middle",
        "font-family": _FONT, "font-size": size, "fill": fill,
    })
    el.text = content
    return el
