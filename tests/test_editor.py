"""Tests for Feature 12: Graphical Config Editor

Tests for the /editor page, JSON submission, and YAML download.
"""
import io
import json
import pytest
from backend import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


EDITOR_JSON = {
    "workers": 2,
    "worker_names": [
        {"name": "Alice", "available_in": 0},
        {"name": "Bob", "available_in": 3},
    ],
    "calendar": {
        "start_date": "2026-03-09",
        "show_weekends": False,
    },
    "projects": [
        {
            "name": "Backend",
            "tasks": [
                {"name": "API", "days": 3, "parallel": False, "depends_on": []},
                {"name": "Docs", "days": 2, "parallel": True, "depends_on": []},
            ],
        },
        {
            "name": "Frontend",
            "tasks": [
                {"name": "UI", "days": 4, "parallel": False, "depends_on": ["Backend/API"]},
            ],
        },
    ],
}


class TestEditorPage:
    """Tests for GET /editor."""

    def test_editor_returns_200(self, client):
        response = client.get("/editor")
        assert response.status_code == 200

    def test_editor_has_project_controls(self, client):
        response = client.get("/editor")
        html = response.data.decode()
        assert "Add Project" in html or "add-project" in html

    def test_editor_has_worker_controls(self, client):
        response = client.get("/editor")
        html = response.data.decode()
        assert "worker" in html.lower()


class TestEditorSubmit:
    """Tests for POST /editor/submit."""

    def test_submit_valid_json_returns_200(self, client):
        response = client.post(
            "/editor/submit",
            data=json.dumps(EDITOR_JSON),
            content_type="application/json",
        )
        assert response.status_code == 200

    def test_submit_returns_schedule_html(self, client):
        response = client.post(
            "/editor/submit",
            data=json.dumps(EDITOR_JSON),
            content_type="application/json",
        )
        html = response.data.decode()
        assert "task-block" in html

    def test_submit_empty_body_returns_400(self, client):
        response = client.post(
            "/editor/submit",
            data="{}",
            content_type="application/json",
        )
        assert response.status_code == 400


class TestEditorDownload:
    """Tests for POST /editor/download (YAML export)."""

    def test_download_returns_yaml(self, client):
        response = client.post(
            "/editor/download",
            data=json.dumps(EDITOR_JSON),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert "yaml" in response.content_type or "text" in response.content_type

    def test_downloaded_yaml_is_valid(self, client):
        import yaml
        response = client.post(
            "/editor/download",
            data=json.dumps(EDITOR_JSON),
            content_type="application/json",
        )
        data = yaml.safe_load(response.data.decode())
        assert "projects" in data

    def test_download_has_attachment_header(self, client):
        response = client.post(
            "/editor/download",
            data=json.dumps(EDITOR_JSON),
            content_type="application/json",
        )
        cd = response.headers.get("Content-Disposition", "")
        assert "attachment" in cd
