from __future__ import annotations

from pathlib import Path
from typing import Any

from planledger.bundle import apply_bundle, load_bundle
from planledger.errors import PlanledgerError
from planledger.models import Workspace
from planledger.storage import list_records


def backfill_apply(
    workspace: Workspace,
    bundle_path: Path,
    *,
    provenance: str = "inferred",
    evidence: list[dict[str, str]] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    bundle = load_bundle(bundle_path)

    if provenance == "inferred" and not evidence:
        raise PlanledgerError(
            "missing_evidence",
            "Inferred backfill requires evidence entries.",
            remediation=[
                "Provide --evidence entries like:",
                '  --evidence path:README.md reason:"Existing goal inferred"',
            ],
        )

    result = apply_bundle(
        workspace,
        bundle,
        dry_run=dry_run,
        provenance=provenance,
    )

    return {
        "kind": "planledger_backfill_apply",
        "provenance": provenance,
        "dry_run": dry_run,
        "created": result.created,
        "reused": result.reused,
        "plan_id": result.plan_id,
        "events": result.events,
    }


def backfill_review(workspace: Workspace) -> dict[str, Any]:
    inferred_records: list[dict[str, Any]] = []

    for kind in (
        "goal",
        "initiative",
        "plan",
        "milestone",
        "slice",
        "decision",
        "risk",
    ):
        for record in list_records(workspace, kind):
            prov = record.front_matter.get("provenance")
            if prov == "inferred":
                inferred_records.append(
                    {
                        "id": record.record_id,
                        "kind": record.kind,
                        "title": record.front_matter.get("title"),
                        "status": record.front_matter.get("status"),
                        "provenance": prov,
                    }
                )

    return {
        "kind": "planledger_backfill_review",
        "inferred_count": len(inferred_records),
        "records": inferred_records,
    }
