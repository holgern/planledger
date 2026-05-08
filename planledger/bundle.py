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
    load_record,
    now_iso,
    save_record,
)


def load_bundle(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PlanledgerError(
            "invalid_bundle",
            f"Bundle is not valid JSON: {exc}",
            remediation=[f"Inspect: {path}"],
        ) from exc
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
    *,
    goal_id: str | None = None,
    initiative_id: str | None = None,
) -> str | None:
    for record in list_records(workspace, kind):
        if record.front_matter.get("title") != title:
            continue
        if goal_id is not None and record.front_matter.get("goal") != goal_id:
            continue
        if initiative_id is not None and (
            record.front_matter.get("initiative") != initiative_id
        ):
            continue
        return record.record_id
    return None


@dataclass
class BundleApplyResult:
    created: list[dict[str, Any]] = field(default_factory=list)
    reused: list[dict[str, Any]] = field(default_factory=list)
    updated: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    plan_id: str | None = None


@dataclass
class _ApplyCtx:
    workspace: Workspace
    run_id: str = ""
    timestamp: str = ""
    actor: str = "agent"
    provenance: str = "agent-generated"
    source_context: list[dict[str, str]] = field(default_factory=list)
    result: BundleApplyResult = field(default_factory=BundleApplyResult)


def _validate_or_raise(bundle: dict[str, Any]) -> None:
    errors = validate_bundle(bundle)
    if errors:
        raise PlanledgerError(
            "invalid_bundle",
            "Bundle validation failed.",
            remediation=errors,
        )


def _resolve_goal(
    ctx: _ApplyCtx,
    goal_data: dict[str, Any],
) -> str | None:
    title = goal_data.get("title", "")
    existing = _find_existing_by_title(ctx.workspace, "goal", title)
    if existing and goal_data.get("reuse") == "active-or-create":
        ctx.result.reused.append({"kind": "goal", "id": existing})
        return existing
    goal_id = allocate_id(ctx.workspace, "goal")
    goal_front = {
        "id": goal_id,
        "type": "goal",
        "title": title,
        "status": "active",
        "horizon": "quarter",
        "priority": "high",
        "success_metrics": [],
        "source_run": ctx.run_id,
        "provenance": ctx.provenance,
        "created_at": ctx.timestamp,
        "updated_at": ctx.timestamp,
    }
    create_record(ctx.workspace, "goal", goal_front, "")
    ctx.result.created.append({"kind": "goal", "id": goal_id})
    return goal_id


def _resolve_initiative(
    ctx: _ApplyCtx,
    init_data: dict[str, Any],
    goal_id: str | None,
) -> str | None:
    title = init_data.get("title", "")
    existing = _find_existing_by_title(ctx.workspace, "initiative", title)
    if existing and init_data.get("reuse") == "active-or-create":
        ctx.result.reused.append({"kind": "initiative", "id": existing})
        return existing
    init_id = allocate_id(ctx.workspace, "initiative")
    init_front = {
        "id": init_id,
        "type": "initiative",
        "goal": goal_id,
        "title": title,
        "status": "shaping",
        "owner": ctx.actor,
        "priority": "high",
        "active": False,
        "source_run": ctx.run_id,
        "provenance": ctx.provenance,
        "created_at": ctx.timestamp,
        "updated_at": ctx.timestamp,
    }
    create_record(ctx.workspace, "initiative", init_front, "")
    ctx.result.created.append({"kind": "initiative", "id": init_id})
    return init_id


def _create_plan(
    ctx: _ApplyCtx,
    plan_data: dict[str, Any],
    goal_id: str | None,
    init_id: str | None,
) -> None:
    if not plan_data or not init_id:
        return
    plan_id = allocate_id(ctx.workspace, "plan")
    body_parts = [
        f"# Plan: {plan_data.get('title', '')}",
        "",
        "## Context",
        "",
    ]
    for ctx_line in plan_data.get("context", []):
        body_parts.append(f"- {ctx_line}")
    body_parts.extend(["", "## Objectives", ""])
    for obj in plan_data.get("objectives", []):
        body_parts.append(f"- {obj}")
    body_parts.append("")
    if plan_data.get("non_goals"):
        body_parts.extend(["## Non-goals", ""])
        for ng in plan_data["non_goals"]:
            body_parts.append(f"- {ng}")
        body_parts.append("")
    plan_body = "\n".join(body_parts)
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
        "source_run": ctx.run_id,
        "provenance": ctx.provenance,
        "created_at": ctx.timestamp,
        "updated_at": ctx.timestamp,
    }
    create_record(ctx.workspace, "plan", plan_front, plan_body)
    ctx.result.created.append({"kind": "plan", "id": plan_id})
    ctx.result.plan_id = plan_id


def _create_milestones_and_slices(
    ctx: _ApplyCtx,
    milestones_data: list[dict[str, Any]],
    init_id: str | None,
    plan_id: str | None,
) -> list[str]:
    created_ids: list[str] = []
    milestone_order = 10
    ws = ctx.workspace
    for ms_data in milestones_data:
        if not isinstance(ms_data, dict):
            continue
        ms_id = allocate_id(ws, "milestone")
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
            "source_run": ctx.run_id,
            "created_at": ctx.timestamp,
            "updated_at": ctx.timestamp,
        }
        create_record(ws, "milestone", ms_front, "")
        ctx.result.created.append({"kind": "milestone", "id": ms_id})
        created_ids.append(ms_id)
        milestone_order += 10
        for sl_data in ms_data.get("slices", []):
            sl_id = _create_slice(
                ctx,
                sl_data,
                init_id,
                plan_id,
                ms_id,
            )
            if sl_id:
                created_ids.append(sl_id)
    return created_ids


def _create_slice(
    ctx: _ApplyCtx,
    sl_data: dict[str, Any],
    init_id: str | None,
    plan_id: str | None,
    ms_id: str,
) -> str | None:
    if not isinstance(sl_data, dict):
        return None
    ws = ctx.workspace
    ext_key = sl_data.get("key")
    if ext_key and init_id:
        existing = _find_existing_by_key(ws, "slice", init_id, ext_key)
        if existing:
            ctx.result.reused.append({"kind": "slice", "id": existing})
            return None
    sl_id = allocate_id(ws, "slice")
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
        "source_run": ctx.run_id,
        "provenance": ctx.provenance,
        "created_at": ctx.timestamp,
        "updated_at": ctx.timestamp,
    }
    if ext_key:
        sl_front["external_key"] = ext_key
    for fname in (
        "objective",
        "target_files",
        "implementation_steps",
        "acceptance_criteria",
        "validation_commands",
    ):
        if sl_data.get(fname):
            sl_front[fname] = sl_data[fname]
    if sl_data.get("ready_for_taskledger"):
        sl_front["ready_for_taskledger"] = True
        sl_front["status"] = "ready-for-execution"
    create_record(ws, "slice", sl_front, "")
    ctx.result.created.append({"kind": "slice", "id": sl_id})
    return sl_id


def _create_decisions_and_options(
    ctx: _ApplyCtx,
    decisions_data: list[dict[str, Any]],
    init_id: str | None,
    plan_id: str | None,
) -> list[str]:
    created_ids: list[str] = []
    ws = ctx.workspace
    for dec_data in decisions_data:
        if not isinstance(dec_data, dict):
            continue
        dec_id = allocate_id(ws, "decision")
        dec_front: dict[str, Any] = {
            "id": dec_id,
            "type": "decision",
            "initiative": init_id,
            "plan": plan_id,
            "title": dec_data.get("title", ""),
            "status": dec_data.get("status", "open"),
            "chosen_option": None,
            "decision_type": dec_data.get("decision_type"),
            "source_run": ctx.run_id,
            "provenance": ctx.provenance,
            "created_at": ctx.timestamp,
            "updated_at": ctx.timestamp,
            "accepted_at": None,
        }
        body = "# Decision\n\n## Context\n\n## Rationale\n\n"
        rationale = dec_data.get("rationale")
        if rationale:
            body += f"{rationale}\n"

        # Build option id map before writing decision
        option_ids_by_title: dict[str, str] = {}
        for opt_data in dec_data.get("options", []):
            if not isinstance(opt_data, dict):
                continue
            opt_id = allocate_id(ws, "option")
            opt_title = str(opt_data.get("title", ""))
            option_ids_by_title[opt_title] = opt_id
            opt_front = {
                "id": opt_id,
                "type": "option",
                "decision": dec_id,
                "title": opt_data.get("title", ""),
                "status": opt_data.get("status", "candidate"),
                "source_run": ctx.run_id,
                "created_at": ctx.timestamp,
                "updated_at": ctx.timestamp,
            }
            create_record(ws, "option", opt_front, "")
            ctx.result.created.append(
                {
                    "kind": "option",
                    "id": opt_id,
                    "title": opt_data.get("title", ""),
                }
            )
            created_ids.append(opt_id)

        # Set chosen_option and accepted_at if accepted
        if dec_data.get("status") == "accepted" and dec_data.get("options"):
            accepted = next(
                (
                    o
                    for o in dec_data["options"]
                    if isinstance(o, dict) and o.get("status") == "accepted"
                ),
                None,
            )
            if accepted:
                dec_front["chosen_option"] = option_ids_by_title.get(
                    str(accepted.get("title", ""))
                )
                dec_front["accepted_at"] = ctx.timestamp

        create_record(ws, "decision", dec_front, body)
        ctx.result.created.append({"kind": "decision", "id": dec_id})
        created_ids.append(dec_id)
    return created_ids


def _create_risks(
    ctx: _ApplyCtx,
    risks_data: list[dict[str, Any]],
    init_id: str | None,
) -> list[str]:
    created_ids: list[str] = []
    ws = ctx.workspace
    for risk_data in risks_data:
        if not isinstance(risk_data, dict):
            continue
        risk_id = allocate_id(ws, "risk")
        risk_front = {
            "id": risk_id,
            "type": "risk",
            "initiative": init_id,
            "title": risk_data.get("title", ""),
            "status": "open",
            "likelihood": risk_data.get("likelihood", "medium"),
            "impact": risk_data.get("impact", "medium"),
            "mitigation": risk_data.get("mitigation", ""),
            "source_run": ctx.run_id,
            "provenance": ctx.provenance,
            "created_at": ctx.timestamp,
            "updated_at": ctx.timestamp,
        }
        create_record(ws, "risk", risk_front, "")
        ctx.result.created.append({"kind": "risk", "id": risk_id})
        created_ids.append(risk_id)
    return created_ids


def apply_bundle(
    workspace: Workspace,
    bundle: dict[str, Any],
    *,
    dry_run: bool = False,
    actor: str = "agent",
    provenance: str = "agent-generated",
    evidence: list[dict[str, str]] | None = None,
) -> BundleApplyResult:
    _validate_or_raise(bundle)
    if dry_run:
        return _preview_bundle(
            workspace,
            bundle,
            actor=actor,
            provenance=provenance,
        )
    ctx = _ApplyCtx(
        workspace=workspace,
        timestamp=now_iso(),
        actor=actor,
        provenance=provenance,
        source_context=evidence or [],
    )
    run_front: dict[str, Any] = {
        "id": "",
        "type": "run",
        "actor": actor,
        "harness": None,
        "skill_version": None,
        "user_request": bundle.get("request", {}).get("title", ""),
        "planning_mode": (bundle.get("request", {}).get("planning_mode", "full")),
        "provenance": provenance,
        "source_context": ctx.source_context,
        "created_records": [],
        "created_at": ctx.timestamp,
        "updated_at": ctx.timestamp,
    }
    ctx.run_id = allocate_id(workspace, "run")
    run_front["id"] = ctx.run_id
    create_record(workspace, "run", run_front, "")
    ctx.result.created.append({"kind": "run", "id": ctx.run_id})

    goal_id = _resolve_goal(ctx, bundle.get("goal", {}))
    init_id = _resolve_initiative(ctx, bundle.get("initiative", {}), goal_id)
    _create_plan(ctx, bundle.get("plan", {}), goal_id, init_id)
    plan_id = ctx.result.plan_id
    ms_ids = _create_milestones_and_slices(
        ctx,
        bundle.get("milestones", []),
        init_id,
        plan_id,
    )
    dec_ids = _create_decisions_and_options(
        ctx,
        bundle.get("decisions", []),
        init_id,
        plan_id,
    )
    risk_ids = _create_risks(ctx, bundle.get("risks", []), init_id)
    all_created = [r["id"] for r in ctx.result.created] + ms_ids + dec_ids + risk_ids
    if all_created:
        run_record = load_record(workspace, "run", ctx.run_id)
        run_record.front_matter["created_records"] = all_created
        run_record.front_matter["source_context"] = ctx.source_context
        save_record(run_record)

    evt = append_event(
        workspace,
        command="planledger bundle apply",
        object_type="run",
        object_id=ctx.run_id,
        event_type="bundle_applied",
        after={
            "created": len(ctx.result.created),
            "reused": len(ctx.result.reused),
        },
        actor=actor,
    )
    ctx.result.events.append(evt)
    return ctx.result


def _preview_bundle(
    workspace: Workspace,
    bundle: dict[str, Any],
    *,
    actor: str = "agent",
    provenance: str = "agent-generated",
) -> BundleApplyResult:
    """Compute what apply_bundle would create without writing anything."""
    result = BundleApplyResult()

    # Simulate goal
    goal_data = bundle.get("goal", {})
    if goal_data:
        title = goal_data.get("title", "")
        existing = _find_existing_by_title(workspace, "goal", title)
        if existing and goal_data.get("reuse") == "active-or-create":
            result.reused.append(
                {
                    "kind": "goal",
                    "id": existing,
                    "title": title,
                }
            )
        else:
            result.created.append(
                {
                    "kind": "goal",
                    "id": "goal-preview",
                    "title": title,
                }
            )

    # Simulate initiative
    init_data = bundle.get("initiative", {})
    if init_data:
        title = init_data.get("title", "")
        existing = _find_existing_by_title(workspace, "initiative", title)
        if existing and init_data.get("reuse") == "active-or-create":
            result.reused.append(
                {
                    "kind": "initiative",
                    "id": existing,
                    "title": title,
                }
            )
        else:
            result.created.append(
                {
                    "kind": "initiative",
                    "id": "init-preview",
                    "title": title,
                }
            )

    # Simulate plan
    plan_data = bundle.get("plan", {})
    if plan_data:
        result.created.append(
            {
                "kind": "plan",
                "title": plan_data.get("title", ""),
            }
        )
        result.plan_id = "plan-preview"

    # Simulate milestones and slices
    for ms_data in bundle.get("milestones", []):
        if not isinstance(ms_data, dict):
            continue
        result.created.append(
            {
                "kind": "milestone",
                "title": ms_data.get("title", ""),
            }
        )
        for sl_data in ms_data.get("slices", []):
            if not isinstance(sl_data, dict):
                continue
            result.created.append(
                {
                    "kind": "slice",
                    "title": sl_data.get("title", ""),
                }
            )

    # Simulate decisions and options
    for dec_data in bundle.get("decisions", []):
        if not isinstance(dec_data, dict):
            continue
        result.created.append(
            {
                "kind": "decision",
                "title": dec_data.get("title", ""),
            }
        )
        for opt_data in dec_data.get("options", []):
            if not isinstance(opt_data, dict):
                continue
            result.created.append(
                {
                    "kind": "option",
                    "title": opt_data.get("title", ""),
                }
            )

    # Simulate risks
    for risk_data in bundle.get("risks", []):
        if not isinstance(risk_data, dict):
            continue
        result.created.append(
            {
                "kind": "risk",
                "title": risk_data.get("title", ""),
            }
        )

    # Simulate run
    result.created.insert(0, {"kind": "run", "title": "preview"})

    return result
