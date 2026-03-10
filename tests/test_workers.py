"""Tests for Feature 10: Named Workers & Availability Offsets in Config

Tests that the parser handles worker_names, available_in, and backward
compatibility with anonymous workers: N.
"""
import pytest
from backend import Config, WorkerInfo, parse_config


class TestWorkerNamesParsing:
    """Tests for parsing worker_names config."""

    def test_named_workers_parsed(self):
        yaml_str = """
worker_names:
  - name: "Alice"
    available_in: 0
  - name: "Bob"
    available_in: 5
projects:
  - name: "P1"
    tasks:
      - name: "T1"
        days: 1
"""
        config = parse_config(yaml_str)
        assert len(config.worker_names) == 2
        assert config.worker_names[0].name == "Alice"
        assert config.worker_names[1].name == "Bob"

    def test_available_in_defaults_to_zero(self):
        yaml_str = """
worker_names:
  - name: "Alice"
projects:
  - name: "P1"
    tasks:
      - name: "T1"
        days: 1
"""
        config = parse_config(yaml_str)
        assert config.worker_names[0].available_in == 0

    def test_anonymous_workers_backward_compatible(self):
        yaml_str = """
workers: 3
projects:
  - name: "P1"
    tasks:
      - name: "T1"
        days: 1
"""
        config = parse_config(yaml_str)
        assert config.workers == 3
        assert len(config.worker_names) == 3
        # Anonymous workers should get default names
        assert config.worker_names[0].name == "Worker 1"

    def test_worker_count_from_named(self):
        yaml_str = """
worker_names:
  - name: "Alice"
  - name: "Bob"
projects:
  - name: "P1"
    tasks:
      - name: "T1"
        days: 1
"""
        config = parse_config(yaml_str)
        assert config.workers == 2

    def test_negative_available_in_raises(self):
        yaml_str = """
worker_names:
  - name: "Alice"
    available_in: -1
projects:
  - name: "P1"
    tasks:
      - name: "T1"
        days: 1
"""
        with pytest.raises(ValueError, match="available_in"):
            parse_config(yaml_str)

    def test_no_workers_at_all_raises(self):
        yaml_str = """
projects:
  - name: "P1"
    tasks:
      - name: "T1"
        days: 1
"""
        with pytest.raises(ValueError, match="workers"):
            parse_config(yaml_str)
