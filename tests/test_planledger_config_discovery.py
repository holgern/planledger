from __future__ import annotations

import json
from pathlib import Path

from planledger.storage import initialize_project, load_workspace_from_root


def test_loads_hidden_planledger_toml(tmp_path: Path) -> None:
    initialize_project(tmp_path, "Hidden Config")
    visible = tmp_path / "planledger.toml"
    hidden = tmp_path / ".planledger.toml"
    hidden.write_text(visible.read_text(encoding="utf-8"), encoding="utf-8")
    visible.unlink()

    loaded = load_workspace_from_root(tmp_path)
    assert loaded.config_path == hidden
    assert loaded.config["project"]["name"] == "Hidden Config"


def test_discovers_hidden_config_from_subdir(invoke, tmp_path: Path) -> None:
    init_result = invoke(tmp_path, "init", "--project-name", "Hidden Config")
    assert init_result.exit_code == 0
    visible = tmp_path / "planledger.toml"
    hidden = tmp_path / ".planledger.toml"
    hidden.write_text(visible.read_text(encoding="utf-8"), encoding="utf-8")
    visible.unlink()

    subdir = tmp_path / "src" / "pkg"
    subdir.mkdir(parents=True)
    status = invoke(subdir, "--json", "status")
    view = invoke(subdir, "--json", "view")
    context = invoke(subdir, "--json", "context", "export")

    assert status.exit_code == 0
    assert view.exit_code == 0
    assert context.exit_code == 0

    status_payload = json.loads(status.stdout)
    assert status_payload["ok"] is True
    assert status_payload["result"]["project"] == "Hidden Config"


def test_hidden_config_preferred_when_both_exist(tmp_path: Path) -> None:
    initialize_project(tmp_path, "Visible")
    hidden = tmp_path / ".planledger.toml"
    hidden.write_text(
        (tmp_path / "planledger.toml")
        .read_text(encoding="utf-8")
        .replace('name = "Visible"', 'name = "Hidden"'),
        encoding="utf-8",
    )

    loaded = load_workspace_from_root(tmp_path)
    assert loaded.config_path == hidden
    assert loaded.config["project"]["name"] == "Hidden"
