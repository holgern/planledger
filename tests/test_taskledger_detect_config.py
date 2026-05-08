from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from planledger.storage import initialize_project
from planledger.taskledger import detect


@pytest.fixture
def workspace(tmp_path: Path):
    return initialize_project(tmp_path, "Config Test")


def test_detect_finds_taskledger_toml(workspace) -> None:
    config_file = workspace.root / "taskledger.toml"
    config_file.write_text("[project]\nname = 'test'\n", encoding="utf-8")
    with patch("planledger.taskledger.shutil.which", return_value=None):
        result = detect(workspace)
    assert result["config_path"] == str(config_file)


def test_detect_finds_hidden_taskledger_toml(workspace) -> None:
    config_file = workspace.root / ".taskledger.toml"
    config_file.write_text("[project]\nname = 'test'\n", encoding="utf-8")
    with patch("planledger.taskledger.shutil.which", return_value=None):
        result = detect(workspace)
    assert result["config_path"] == str(config_file)


def test_detect_prefers_hidden_config(workspace) -> None:
    hidden = workspace.root / ".taskledger.toml"
    visible = workspace.root / "taskledger.toml"
    hidden.write_text("[project]\nname = 'hidden'\n", encoding="utf-8")
    visible.write_text("[project]\nname = 'visible'\n", encoding="utf-8")
    with patch("planledger.taskledger.shutil.which", return_value=None):
        result = detect(workspace)
    assert ".taskledger.toml" in result["config_path"]


def test_detect_no_config(workspace) -> None:
    with patch("planledger.taskledger.shutil.which", return_value=None):
        result = detect(workspace)
    assert result["detected"] is False


def test_detect_uses_config_file_override(workspace) -> None:
    hidden = workspace.root / ".custom-taskledger.toml"
    hidden.write_text("[project]\nname = 'custom'\n", encoding="utf-8")
    workspace.config.setdefault("integrations", {}).setdefault("taskledger", {})[
        "config_file"
    ] = ".custom-taskledger.toml"
    with patch("planledger.taskledger.shutil.which", return_value=None):
        result = detect(workspace)
    assert result["config_path"] == str(hidden.resolve())
