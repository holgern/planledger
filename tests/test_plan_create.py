from __future__ import annotations

from pathlib import Path

import yaml


def test_plan_create_builds_component_layout_and_rendered_artifact(
    initialized_workspace: Path, invoke
) -> None:
    first = invoke(
        initialized_workspace,
        "plan",
        "create",
        "--title",
        "Add feature A",
        "--request",
        "Please review how we can add feature A.",
    )
    second = invoke(
        initialized_workspace,
        "plan",
        "create",
        "--title",
        "Add feature B",
        "--request",
        "Please review how we can add feature B.",
    )

    assert first.exit_code == 0, first.stdout
    assert second.exit_code == 0, second.stdout

    plan_dir = initialized_workspace / ".planledger" / "plans" / "plan-0001"
    metadata = yaml.safe_load((plan_dir / "plan.yaml").read_text())

    assert metadata["id"] == "plan-0001"
    assert metadata["status"] == "new"
    assert metadata["version"] == 1
    assert (plan_dir / "components").is_dir()
    assert (plan_dir / "rendered" / "latest.md").exists()
    assert (plan_dir / "versions" / "v0001").is_dir()
    assert (initialized_workspace / ".planledger" / "plans" / "plan-0002").is_dir()
    assert not (initialized_workspace / ".planledger" / "ledgers" / "main").exists()


def test_plan_create_sets_active_plan(initialized_workspace: Path, invoke) -> None:
    result = invoke(
        initialized_workspace,
        "plan",
        "create",
        "--title",
        "Add feature A",
        "--request",
        "Please review how we can add feature A.",
    )
    assert result.exit_code == 0, result.stdout

    storage = yaml.safe_load(
        (initialized_workspace / ".planledger" / "storage.yaml").read_text()
    )
    assert storage["active_plan_id"] == "plan-0001"


def test_plan_create_replaces_active_plan(initialized_workspace: Path, invoke) -> None:
    invoke(
        initialized_workspace,
        "plan",
        "create",
        "--title",
        "First",
        "--request",
        "First request.",
    )
    second = invoke(
        initialized_workspace,
        "plan",
        "create",
        "--title",
        "Second",
        "--request",
        "Second request.",
    )
    assert second.exit_code == 0, second.stdout

    storage = yaml.safe_load(
        (initialized_workspace / ".planledger" / "storage.yaml").read_text()
    )
    assert storage["active_plan_id"] == "plan-0002"
