"""Tests for Feature 17: SVG Chart Export

Tests for the /export/svg endpoint, SVG content verification,
and the export button on the schedule page.
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
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestSVGExportRoute:
    """Tests for POST /export/svg endpoint."""

    def test_export_svg_returns_200(self, client):
        """Valid YAML produces a 200 response."""
        resp = client.post("/export/svg",
                           data={"config_yaml": VALID_YAML.decode()})
        assert resp.status_code == 200

    def test_export_svg_content_type(self, client):
        """Response content type is image/svg+xml."""
        resp = client.post("/export/svg",
                           data={"config_yaml": VALID_YAML.decode()})
        assert "svg" in resp.content_type

    def test_export_svg_has_attachment_header(self, client):
        """Response has a Content-Disposition attachment header."""
        resp = client.post("/export/svg",
                           data={"config_yaml": VALID_YAML.decode()})
        cd = resp.headers.get("Content-Disposition", "")
        assert "attachment" in cd
        assert "schedule.svg" in cd

    def test_export_svg_contains_svg_element(self, client):
        """Response body contains a valid SVG root element."""
        resp = client.post("/export/svg",
                           data={"config_yaml": VALID_YAML.decode()})
        body = resp.data.decode()
        assert "<svg" in body
        assert "</svg>" in body

    def test_export_svg_contains_task_names(self, client):
        """SVG output includes task names as text."""
        resp = client.post("/export/svg",
                           data={"config_yaml": VALID_YAML.decode()})
        body = resp.data.decode()
        assert "Setup DB" in body
        assert "Auth endpoints" in body

    def test_export_svg_contains_worker_labels(self, client):
        """SVG output includes worker labels."""
        resp = client.post("/export/svg",
                           data={"config_yaml": VALID_YAML.decode()})
        body = resp.data.decode()
        assert "Worker 1" in body
        assert "Worker 2" in body

    def test_export_svg_contains_project_legend(self, client):
        """SVG output includes project names in the legend."""
        resp = client.post("/export/svg",
                           data={"config_yaml": VALID_YAML.decode()})
        body = resp.data.decode()
        assert "Backend API" in body
        assert "Frontend" in body

    def test_export_svg_no_config_returns_400(self, client):
        """Missing config_yaml returns 400."""
        resp = client.post("/export/svg", data={})
        assert resp.status_code == 400

    def test_export_svg_invalid_yaml_returns_400(self, client):
        """Invalid YAML returns 400."""
        resp = client.post("/export/svg",
                           data={"config_yaml": "workers: not_a_number"})
        assert resp.status_code == 400


class TestSchedulePageExportButton:
    """Tests that the schedule page contains an SVG export control."""

    def test_schedule_has_export_button(self, client):
        """Schedule page from file upload includes an SVG export form."""
        data = {"file": (io.BytesIO(VALID_YAML), "config.yaml")}
        resp = client.post("/upload", data=data,
                           content_type="multipart/form-data")
        html = resp.data.decode()
        assert "export/svg" in html
        assert "Export SVG" in html
