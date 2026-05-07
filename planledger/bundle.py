from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from planledger.errors import PlanledgerError
from planledger.models import Workspace
from planledger.storage import (
    allocate_id,
    append_event,
    create_record,
    list_records,
    now_iso,
)


def load_bundle(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise PlanledgerError(
            "invalid_bundle",
            "Bundle must be a JSON object.",
            remediation=[f"Inspect: {path}"],
        )
    return data


def validate_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    schema = bundle.get("schema")
    if schema != "planledger.plan_bundle.v1":
        errors.append(
            f"Missing or invalid schema: expected "
            f"'planledger.plan_bundle.v1', got {schema!r}."
        )

    plan_data = bundle.get("plan")
    if not isinstance(plan_data, dict):
        errors.append("Missing or invalid 'plan' section.")
    else:
        if not plan_data.get("title"):
            errors.append("Plan title is required.")
        if not plan_data.get("objectives"):
            errors.append("Plan objectives are required.")

    request_data = bundle.get("request")
    if not isinstance(request_data, dict):
        errors.append("Missing or invalid 'request' section.")

    milestones = bundle.get("milestones")
    if milestones is not None:
        if not isinstance(milestones, list):
            errors.append("'milestones' must be a list.")
        else:
            for i, ms in enumerate(milestones):
                if not isinstance(ms, dict):
                    errors.append(f"Milestone {i} must be an object.")
                    continue
                if not ms.get("title"):
                    errors.append(f"Milestone {i} missing title.")
                slices = ms.get("slices", [])
                for j, sl in enumerate(slices):
                    if not isinstance(sl, dict):
                        errors.append(f"Milestone {i} slice {j} must be an object.")
                        continue
                    if not sl.get("title"):
                        errors.append(f"Milestone {i} slice {j} missing title.")

    decisions = bundle.get("decisions")
    if decisions is not None:
        if not isinstance(decisions, list):
            errors.append("'decisions' must be a list.")

    risks = bundle.get("risks")
    if risks is not None:
        if not isinstance(risks, list):
            errors.append("'risks' must be a list.")

    return errors


def _find_existing_by_key(
    workspace: Workspace,
    kind: str,
    initiative_id: str,
    external_key: str,
) -> str | None:
    for record in list_records(workspace, kind):
        if (
            record.front_matter.get("initiative") == initiative_id
            and record.front_matter.get("external_key") == external_key
        ):
            return record.record_id
    return None


def _find_existing_by_title(
    workspace: Workspace,
    kind: str,
    title: str,
) -> str | None:
    for record in list_records(workspace, kind):
        if record.front_matter.get("title") == title:
            return record.record_id
    return None


@dataclass
class BundleApplyResult:
    created: list[dict[str, Any]] = field(default_factory=list)
    reused: list[dict[str, Any]] = field(default_factory=list)
    updated: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    plan_id: str | None = None


def apply_bundle(
    workspace: Workspace,
    bundle: dict[str, Any],
    *,
    dry_run: bool = False,
    actor: str = "agent",
    provenance: str = "agent-generated",
) -> BundleApplyResult:
    result = BundleApplyResult()
    timestamp = now_iso()

    if dry_run:
        return result

    errors = validate_bundle(bundle)
    if errors:
        raise PlanledgerError(
            "invalid_bundle",
            "Bundle validation failed.",
            remediation=errors,
        )

    request_data = bundle.get("request", {})

    run_id = allocate_id(workspace, "run")
    run_front: dict[str, Any] = {
        "id": run_id,
        "type": "run",
        "actor": actor,
        "harness": None,
        "skill_version": None,
        "user_request": request_data.get("title", ""),
        "planning_mode": request_data.get("planning_mode", "full"),
        "provenance": provenance,
        "source_context": [],
        "created_records": [],
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    create_record(workspace, "run", run_front, "")
    result.created.append({"kind": "run", "id": run_id})

    goal_data = bundle.get("goal", {})
    goal_id = None
    if goal_data:
        reuse_mode = goal_data.get("reuse", "")
        title = goal_data.get("title", "")
        existing = _find_existing_by_title(workspace, "goal", title)
        if existing and reuse_mode == "active-or-create":
            goal_id = existing
            result.reused.append({"kind": "goal", "id": goal_id})
        else:
            goal_id = allocate_id(workspace, "goal")
            goal_front = {
                "id": goal_id,
                "type": "goal",
                "title": title,
                "status": "active",
                "horizon": "quarter",
                "priority": "high",
                "success_metrics": [],
                "source_run": run_id,
                "provenance": provenance,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            create_record(workspace, "goal", goal_front, "")
            result.created.append({"kind": "goal", "id": goal_id})

    init_data = bundle.get("initiative", {})
    init_id = None
    if init_data:
        reuse_mode = init_data.get("reuse", "")
        title = init_data.get("title", "")
        existing = _find_existing_by_title(
            workspace,
            "initiative",
            title,
        )
        if existing and reuse_mode == "active-or-create":
            init_id = existing
            result.reused.append({"kind": "initiative", "id": init_id})
        else:
            init_id = allocate_id(workspace, "initiative")
            init_front = {
                "id": init_id,
                "type": "initiative",
                "goal": goal_id,
                "title": title,
                "status": "shaping",
                "owner": actor,
                "priority": "high",
                "active": False,
                "source_run": run_id,
                "provenance": provenance,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            create_record(workspace, "initiative", init_front, "")
            result.created.append({"kind": "initiative", "id": init_id})

    plan_data = bundle.get("plan", {})
    plan_id = None
    if plan_data and init_id:
        plan_id = allocate_id(workspace, "plan")
        plan_body_parts = [
            f"# Plan: {plan_data.get('title', '')}",
            "",
            "## Context",
            "",
        ]
        for ctx_line in plan_data.get("context", []):
            plan_body_parts.append(f"- {ctx_line}")
        plan_body_parts.append("")
        plan_body_parts.append("## Objectives")
        plan_body_parts.append("")
        for obj in plan_data.get("objectives", []):
            plan_body_parts.append(f"- {obj}")
        plan_body_parts.append("")
        if plan_data.get("non_goals"):
            plan_body_parts.append("## Non-goals")
            plan_body_parts.append("")
            for ng in plan_data["non_goals"]:
                plan_body_parts.append(f"- {ng}")
            plan_body_parts.append("")

        plan_body = "\n".join(plan_body_parts)
        plan_front = {
            "id": plan_id,
            "type": "plan",
            "goal": goal_id,
            "initiative": init_id,
            "version": 1,
            "status": "draft",
            "supersedes": None,
            "accepted_at": None,
            "accepted_by": None,
            "source_run": run_id,
            "provenance": provenance,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        create_record(workspace, "plan", plan_front, plan_body)
        result.created.append({"kind": "plan", "id": plan_id})
        result.plan_id = plan_id

    created_record_ids: list[str] = [r["id"] for r in result.created]

    milestones_data = bundle.get("milestones", [])
    milestone_order = 10
    for ms_data in milestones_data:
        if not isinstance(ms_data, dict):
            continue
        ms_id = allocate_id(workspace, "milestone")
        ms_front = {
            "id": ms_id,
            "type": "milestone",
            "initiative": init_id,
            "plan": plan_id,
            "title": ms_data.get("title", ""),
            "status": "planned",
            "order": milestone_order,
            "target": None,
            "exit_criteria": [],
            "source_run": run_id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        create_record(workspace, "milestone", ms_front, "")
        result.created.append({"kind": "milestone", "id": ms_id})
        created_record_ids.append(ms_id)
        milestone_order += 10

        for sl_data in ms_data.get("slices", []):
            if not isinstance(sl_data, dict):
                continue
            ext_key = sl_data.get("key")
            existing_slice = None
            if ext_key and init_id:
                existing_slice = _find_existing_by_key(
                    workspace,
                    "slice",
                    init_id,
                    ext_key,
                )
            if existing_slice:
                result.reused.append({"kind": "slice", "id": existing_slice})
                continue

            sl_id = allocate_id(workspace, "slice")
            sl_front: dict[str, Any] = {
                "id": sl_id,
                "type": "slice",
                "initiative": init_id,
                "plan": plan_id,
                "milestone": ms_id,
                "title": sl_data.get("title", ""),
                "status": "shaping",
                "priority": "high",
                "size": "M",
                "risk": "medium",
                "depends_on": [],
                "blocked_by": [],
                "taskledger_bindings": [],
                "source_run": run_id,
                "provenance": provenance,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            if ext_key:
                sl_front["external_key"] = ext_key
            if sl_data.get("objective"):
                sl_front["objective"] = sl_data["objective"]
            if sl_data.get("target_files"):
                sl_front["target_files"] = sl_data["target_files"]
            if sl_data.get("implementation_steps"):
                sl_front["implementation_steps"] = sl_data["implementation_steps"]
            if sl_data.get("acceptance_criteria"):
                sl_front["acceptance_criteria"] = sl_data["acceptance_criteria"]
            if sl_data.get("validation_commands"):
                sl_front["validation_commands"] = sl_data["validation_commands"]
            if sl_data.get("ready_for_taskledger"):
                sl_front["ready_for_taskledger"] = True
                sl_front["status"] = "ready-for-execution"
            create_record(workspace, "slice", sl_front, "")
            result.created.append({"kind": "slice", "id": sl_id})
            created_record_ids.append(sl_id)

    decisions_data = bundle.get("decisions", [])
    for dec_data in decisions_data:
        if not isinstance(dec_data, dict):
            continue
        dec_id = allocate_id(workspace, "decision")
        dec_front = {
            "id": dec_id,
            "type": "decision",
            "initiative": init_id,
            "plan": plan_id,
            "title": dec_data.get("title", ""),
            "status": dec_data.get("status", "open"),
            "chosen_option": None,
            "decision_type": dec_data.get("decision_type"),
            "source_run": run_id,
            "provenance": provenance,
            "created_at": timestamp,
            "updated_at": timestamp,
            "accepted_at": None,
        }
        body = "# Decision\n\n## Context\n\n## Rationale\n\n"
        rationale = dec_data.get("rationale")
        if rationale:
            body += f"{rationale}\n"
        create_record(workspace, "decision", dec_front, body)
        result.created.append({"kind": "decision", "id": dec_id})
        created_record_ids.append(dec_id)

        for opt_data in dec_data.get("options", []):
            if not isinstance(opt_data, dict):
                continue
            opt_id = allocate_id(workspace, "option")
            opt_front = {
                "id": opt_id,
                "type": "option",
                "decision": dec_id,
                "title": opt_data.get("title", ""),
                "status": opt_data.get("status", "candidate"),
                "source_run": run_id,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            create_record(workspace, "option", opt_front, "")
            result.created.append({"kind": "option", "id": opt_id})
            created_record_ids.append(opt_id)

        if dec_data.get("status") == "accepted" and dec_data.get("options"):
            accepted_opts = [
                o for o in dec_data["options"] if o.get("status") == "accepted"
            ]
            if accepted_opts:
                for r in result.created:
                    if r["kind"] == "option" and r.get("title") == accepted_opts[0].get(
                        "title"
                    ):
                        dec_front["chosen_option"] = r["id"]
                        break

    risks_data = bundle.get("risks", [])
    for risk_data in risks_data:
        if not isinstance(risk_data, dict):
            continue
        risk_id = allocate_id(workspace, "risk")
        risk_front = {
            "id": risk_id,
            "type": "risk",
            "initiative": init_id,
            "title": risk_data.get("title", ""),
            "status": "open",
            "likelihood": risk_data.get("likelihood", "medium"),
            "impact": risk_data.get("impact", "medium"),
            "mitigation": risk_data.get("mitigation", ""),
            "source_run": run_id,
            "provenance": provenance,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        create_record(workspace, "risk", risk_front, "")
        result.created.append({"kind": "risk", "id": risk_id})
        created_record_ids.append(risk_id)

    if created_record_ids:
        from planledger.storage import load_record, save_record

        run_record = load_record(workspace, "run", run_id)
        run_record.front_matter["created_records"] = created_record_ids
        save_record(run_record)

    evt = append_event(
        workspace,
        command="planledger bundle apply",
        object_type="run",
        object_id=run_id,
        event_type="bundle_applied",
        after={
            "created": len(result.created),
            "reused": len(result.reused),
        },
        actor=actor,
    )
    result.events.append(evt)

    return result
