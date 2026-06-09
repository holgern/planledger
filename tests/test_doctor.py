from __future__ import annotations

from pathlib import Path


def test_doctor_reports_healthy_workspace(
    initialized_workspace: Path, invoke_json
) -> None:
    result, payload = invoke_json(initialized_workspace, "doctor")

    assert result.exit_code == 0, result.stdout
    assert payload["result"]["healthy"] is True


def test_doctor_reports_old_schema_detection(
    initialized_workspace: Path, invoke_json
) -> None:
    legacy_dir = initialized_workspace / ".planledger" / "ledgers" / "main"
    legacy_dir.mkdir(parents=True)

    result, payload = invoke_json(initialized_workspace, "doctor")

    assert result.exit_code == 0, result.stdout
    assert payload["result"]["healthy"] is False
    assert any(
        "old schema detected" in error.lower() for error in payload["result"]["errors"]
    )


def test_status_human_output(initialized_workspace: Path, invoke) -> None:
    result = invoke(initialized_workspace, "status")
    assert result.exit_code == 0, result.stdout
    lines = result.stdout.strip().split("\n")
    assert lines[0] == "Planledger status"
    assert any(line.startswith("Workspace:") for line in lines)
    assert any(line.startswith("Config:") for line in lines)
    assert any(line.startswith("Project:") for line in lines)
    assert any(line.startswith("Counts:") for line in lines)
    assert any("Health: not checked" in line for line in lines)
    assert any(line.startswith("Next:") for line in lines)


def test_status_no_check_does_not_run_doctor(
    initialized_workspace: Path, invoke
) -> None:
    result = invoke(initialized_workspace, "status")
    assert result.exit_code == 0, result.stdout
    assert "Health: not checked (use --check)" in result.stdout


def test_status_check_runs_doctor(initialized_workspace: Path, invoke) -> None:
    result = invoke(initialized_workspace, "status", "--check")
    assert result.exit_code == 0, result.stdout
    assert "Health: healthy" in result.stdout


def test_status_shows_active_plan(initialized_workspace: Path, invoke) -> None:
    invoke(
        initialized_workspace,
        "plan", "create", "--title", "Active Plan", "--request", "req",
    )
    result = invoke(initialized_workspace, "status")
    assert result.exit_code == 0, result.stdout
    assert "Active plan: plan-0001 Active Plan (new)" in result.stdout
