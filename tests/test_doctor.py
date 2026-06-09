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
