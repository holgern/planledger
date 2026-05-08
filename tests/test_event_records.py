from __future__ import annotations

from pathlib import Path

from planledger.storage import append_event, initialize_project, list_events


def test_append_event_stores_extended_metadata(tmp_path: Path) -> None:
    workspace = initialize_project(tmp_path, "Event Metadata")
    event = append_event(
        workspace,
        command="planledger taskledger push slice-0001 --create-task",
        object_type="slice",
        object_id="slice-0001",
        event_type="taskledger_binding_created",
        source_run="run-0001",
        provenance="taskledger",
        correlation_id="bind-0001",
        external_command={
            "command": "taskledger --json task create slice --description long text",
            "args": [
                "taskledger",
                "--json",
                "task",
                "create",
                "slice",
                "--description",
                "long text",
            ],
        },
        duration_ms=42,
    )
    assert event["source_run"] == "run-0001"
    assert event["provenance"] == "taskledger"
    assert event["correlation_id"] == "bind-0001"
    assert event["duration_ms"] == 42
    assert event["external_command"]["args"][-1] == "<omitted>"

    listed = list_events(workspace, limit=1)
    assert listed[0]["id"] == event["id"]


def test_append_event_redacts_description_payload(tmp_path: Path) -> None:
    workspace = initialize_project(tmp_path, "Event Redaction")
    event = append_event(
        workspace,
        command='planledger taskledger push slice-0001 --description "very secret details"',
        object_type="slice",
        object_id="slice-0001",
        event_type="updated",
    )
    assert "--description <omitted>" in event["command"]
