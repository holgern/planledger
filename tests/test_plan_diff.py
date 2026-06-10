from __future__ import annotations

from pathlib import Path


def test_diff_includes_changed_component_content(
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
    first_update = invoke(
        initialized_workspace,
        "plan",
        "component",
        "set",
        "summary",
        "--text",
        "First summary.",
    )
    second_update = invoke(
        initialized_workspace,
        "plan",
        "component",
        "set",
        "summary",
        "--text",
        "Second summary.",
    )
    diff = invoke(
        initialized_workspace,
        "plan",
        "diff",
        "plan-0001",
        "--from",
        "v0002",
        "--to",
        "v0003",
    )
    unknown = invoke(
        initialized_workspace,
        "plan",
        "diff",
        "plan-0001",
        "--from",
        "v0099",
        "--to",
        "v0003",
    )

    assert create.exit_code == 0, create.stdout
    assert first_update.exit_code == 0, first_update.stdout
    assert second_update.exit_code == 0, second_update.stdout
    assert diff.exit_code == 0, diff.stdout
    assert "-First summary." in diff.stdout
    assert "+Second summary." in diff.stdout
    assert unknown.exit_code != 0


def test_diff_uses_active_plan(initialized_workspace: Path, invoke) -> None:
    invoke(
        initialized_workspace,
        "plan",
        "create",
        "--title",
        "Active",
        "--request",
        "req",
    )
    invoke(
        initialized_workspace,
        "plan",
        "component",
        "set",
        "summary",
        "--text",
        "Updated.",
    )
    result = invoke(
        initialized_workspace,
        "plan",
        "diff",
        "--from",
        "v0001",
        "--to",
        "v0002",
    )
    assert result.exit_code == 0, result.stdout
    assert "+Updated." in result.stdout
