"""Tests for manifest.json and hacs.json metadata."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_contents():
    path = ROOT / "custom_components" / "openwindows" / "manifest.json"
    data = json.loads(path.read_text())
    assert data["domain"] == "openwindows"
    assert data["name"] == "OpenWindows"
    assert data["config_flow"] is True
    assert data["iot_class"] == "calculated"
    assert data["dependencies"] == ["weather"]
    assert data["after_dependencies"] == ["http", "lovelace", "recorder"]
    assert data["requirements"] == []
    assert data["codeowners"] == ["@MicPiePro"]
    assert data["version"] == "0.1.0"


def test_hacs_contents():
    data = json.loads((ROOT / "hacs.json").read_text())
    assert data["name"] == "OpenWindows"
    assert data["homeassistant"] == "2024.6.0"
    assert data["zip_release"] is True
    assert data["filename"] == "openwindows.zip"
    assert data["content_in_root"] is False
