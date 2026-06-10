from __future__ import annotations

from pathlib import Path


def test_versions_lists_snapshot_directories(
    initialized_workspace: Path, invoke
) -> None:
    create = invoke(
        initialized_workspace,
        "plan",
        "create",
        "--title",
        "Add feature A",
        "--request",
        "Please review how we can add feature A.",
    )
    update = invoke(
        initialized_workspace,
        "plan",
        "component",
        "set",
        "summary",
        "--text",
        "Short summary.",
    )
    versions = invoke(initialized_workspace, "plan", "versions", "plan-0001")

    assert create.exit_code == 0, create.stdout
    assert update.exit_code == 0, update.stdout
    assert versions.exit_code == 0, versions.stdout
    assert "v0001" in versions.stdout
    assert "v0002" in versions.stdout


def test_versions_uses_active_plan(initialized_workspace: Path, invoke) -> None:
    invoke(
        initialized_workspace,
        "plan",
        "create",
        "--title",
        "Active",
        "--request",
        "req",
    )
    result = invoke(
        initialized_workspace,
        "plan",
        "versions",
    )
    assert result.exit_code == 0, result.stdout
    assert "v0001" in result.stdout
