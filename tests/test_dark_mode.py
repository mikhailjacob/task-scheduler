"""Tests for Feature 18: Dark Mode

Tests for dark mode CSS variables, theme toggle button, and theme
initialization script across all pages.
"""
import io

import pytest

from backend import create_app

VALID_YAML = b"""workers: 2

projects:
  - name: "Backend"
    tasks:
      - name: "Task 1"
        days: 3
"""


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestDarkModeToggle:
    """Tests that all pages include the theme toggle button."""

    def test_index_has_theme_toggle(self, client):
        """Landing page includes a theme toggle button."""
        html = client.get("/").data.decode()
        assert "theme-toggle" in html

    def test_editor_has_theme_toggle(self, client):
        """Editor page includes a theme toggle button."""
        html = client.get("/editor").data.decode()
        assert "theme-toggle" in html

    def test_schedule_has_theme_toggle(self, client):
        """Schedule page includes a theme toggle button."""
        data = {"file": (io.BytesIO(VALID_YAML), "config.yaml")}
        resp = client.post("/upload", data=data,
                           content_type="multipart/form-data")
        html = resp.data.decode()
        assert "theme-toggle" in html


class TestDarkModeCSS:
    """Tests that CSS supports dark mode theming."""

    def test_common_css_has_theme_variables(self, client):
        """common.css defines CSS custom properties for theming."""
        css = client.get("/assets/styles/common.css").data.decode()
        assert "--bg" in css

    def test_common_css_has_dark_overrides(self, client):
        """common.css defines [data-theme="dark"] overrides."""
        css = client.get("/assets/styles/common.css").data.decode()
        assert 'data-theme="dark"' in css

    def test_theme_js_accessible(self, client):
        """theme.js is served as a static file."""
        resp = client.get("/assets/js/theme.js")
        assert resp.status_code == 200
        assert "toggleTheme" in resp.data.decode()


class TestDarkModeThemeInit:
    """Tests that pages include the inline theme initializer."""

    def test_index_has_theme_init(self, client):
        """Landing page has inline theme init script."""
        html = client.get("/").data.decode()
        assert "localStorage" in html

    def test_editor_has_theme_init(self, client):
        """Editor page has inline theme init script."""
        html = client.get("/editor").data.decode()
        assert "localStorage" in html

    def test_schedule_has_theme_init(self, client):
        """Schedule page has inline theme init script."""
        data = {"file": (io.BytesIO(VALID_YAML), "config.yaml")}
        resp = client.post("/upload", data=data,
                           content_type="multipart/form-data")
        html = resp.data.decode()
        assert "localStorage" in html
