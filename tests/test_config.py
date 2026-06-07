"""Tests for configuration loading."""
from pathlib import Path
from src.config import Settings, PROJECT_ROOT


def test_project_root_exists():
    assert PROJECT_ROOT.exists()


def test_default_settings():
    s = Settings()
    assert s.extraction_model == "claude-haiku-4-5-20251001"
    assert s.query_model == "claude-sonnet-4-6"
    assert isinstance(s.docs_dir, Path)
    assert isinstance(s.db_path, Path)


def test_has_api_key_false_when_missing():
    s = Settings(anthropic_api_key=None)
    assert s.has_api_key is False


def test_has_api_key_true_when_set():
    s = Settings(anthropic_api_key="sk-test-key")
    assert s.has_api_key is True
