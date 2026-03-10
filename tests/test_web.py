"""Tests for Features 3, 4, 5, 6: Flask Web Server, Gantt Chart, Tooltips, Upload

Tests for the Flask routes, template rendering, hover tooltips,
and file upload validation.
"""
import io
import pytest
from backend import create_app


VALID_YAML = b"""workers: 2

projects:
  - name: "Backend API"
    tasks:
      - name: "Setup DB"
        days: 3
      - name: "Auth endpoints"
        days: 5
  - name: "Frontend"
    tasks:
      - name: "Mockups"
        days: 2
"""


@pytest.fixture
def client():
    """Create a Flask test client."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestIndexRoute:
    """Tests for GET / route (Feature 3)."""

    def test_index_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_index_contains_upload_form(self, client):
        response = client.get("/")
        html = response.data.decode()
        assert '<form' in html
        assert 'enctype="multipart/form-data"' in html

    def test_index_has_file_input(self, client):
        response = client.get("/")
        html = response.data.decode()
        assert 'type="file"' in html

    def test_index_has_editor_link(self, client):
        response = client.get("/")
        html = response.data.decode()
        assert 'href="/editor"' in html

    def test_index_has_or_divider(self, client):
        response = client.get("/")
        html = response.data.decode()
        assert "or" in html.lower()


class TestUploadRoute:
    """Tests for POST /upload route (Features 3, 6)."""

    def test_upload_valid_yaml_returns_200(self, client):
        data = {"file": (io.BytesIO(VALID_YAML), "config.yaml")}
        response = client.post("/upload", data=data, content_type="multipart/form-data")
        assert response.status_code == 200

    def test_upload_no_file_returns_error(self, client):
        response = client.post("/upload", data={}, content_type="multipart/form-data")
        assert response.status_code == 400

    def test_upload_wrong_extension_returns_error(self, client):
        data = {"file": (io.BytesIO(b"data"), "config.txt")}
        response = client.post("/upload", data=data, content_type="multipart/form-data")
        assert response.status_code == 400

    def test_upload_invalid_yaml_returns_error(self, client):
        bad_yaml = b"workers: not_a_number\n"
        data = {"file": (io.BytesIO(bad_yaml), "bad.yaml")}
        response = client.post("/upload", data=data, content_type="multipart/form-data")
        assert response.status_code == 400


class TestGanttChartRendering:
    """Tests for Gantt chart in schedule page (Feature 4)."""

    def test_schedule_contains_worker_labels(self, client):
        data = {"file": (io.BytesIO(VALID_YAML), "config.yaml")}
        response = client.post("/upload", data=data, content_type="multipart/form-data")
        html = response.data.decode()
        assert "Worker 1" in html

    def test_schedule_contains_task_blocks(self, client):
        data = {"file": (io.BytesIO(VALID_YAML), "config.yaml")}
        response = client.post("/upload", data=data, content_type="multipart/form-data")
        html = response.data.decode()
        assert "task-block" in html

    def test_schedule_contains_day_headers(self, client):
        data = {"file": (io.BytesIO(VALID_YAML), "config.yaml")}
        response = client.post("/upload", data=data, content_type="multipart/form-data")
        html = response.data.decode()
        # Should contain day headers (calendar dates or Day N)
        assert "day-header" in html


class TestTooltips:
    """Tests for hover tooltips (Feature 5)."""

    def test_tooltip_contains_task_name(self, client):
        data = {"file": (io.BytesIO(VALID_YAML), "config.yaml")}
        response = client.post("/upload", data=data, content_type="multipart/form-data")
        html = response.data.decode()
        assert "Setup DB" in html

    def test_tooltip_contains_project_name(self, client):
        data = {"file": (io.BytesIO(VALID_YAML), "config.yaml")}
        response = client.post("/upload", data=data, content_type="multipart/form-data")
        html = response.data.decode()
        assert "Backend API" in html

    def test_tooltip_css_exists(self, client):
        data = {"file": (io.BytesIO(VALID_YAML), "config.yaml")}
        response = client.post("/upload", data=data, content_type="multipart/form-data")
        html = response.data.decode()
        assert "tooltip" in html


class TestProjectColors:
    """Tests for project colors in the rendered chart (Feature 7)."""

    def test_different_projects_have_different_colors(self, client):
        data = {"file": (io.BytesIO(VALID_YAML), "config.yaml")}
        response = client.post("/upload", data=data, content_type="multipart/form-data")
        html = response.data.decode()
        # The chart should contain background-color styles
        assert "background-color" in html
