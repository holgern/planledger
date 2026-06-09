from __future__ import annotations

from pathlib import Path


def test_config_discovery_works_from_nested_directories(tmp_path: Path, invoke) -> None:
    root = tmp_path / "repo"
    nested = root / "src" / "pkg"
    nested.mkdir(parents=True)

    init = invoke(root, "init", "--project-name", "Nested Project")
    status = invoke(nested, "status")

    assert init.exit_code == 0, init.stdout
    assert status.exit_code == 0, status.stdout
    assert "Planledger status" in status.stdout


def test_hidden_config_is_discovered_from_nested_directories(
    tmp_path: Path, invoke
) -> None:
    root = tmp_path / "repo"
    nested = root / "child"
    nested.mkdir(parents=True)

    init = invoke(root, "init", "--project-name", "Nested Project", "--hidden-config")
    status = invoke(nested, "status")

    assert init.exit_code == 0, init.stdout
    assert (root / ".planledger.toml").exists()
    assert status.exit_code == 0, status.stdout
