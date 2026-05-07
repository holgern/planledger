from __future__ import annotations

from planledger.models import Record


def render_taskledger_description(
    *,
    slice_record: Record,
    plan: Record,
    milestone: Record,
    decisions: list[Record],
    risks: list[Record],
) -> str:
    lines: list[str] = []

    lines.append(f"# {slice_record.front_matter.get('title', 'Untitled slice')}")
    lines.append("")

    objective = slice_record.front_matter.get("objective")
    if objective:
        lines.append("## Objective")
        lines.append("")
        lines.append(str(objective))
        lines.append("")

    lines.append("## Source")
    lines.append("")
    lines.append(f"- Plan: {plan.record_id}")
    lines.append(f"- Milestone: {milestone.record_id}")
    lines.append(f"- Slice: {slice_record.record_id}")
    lines.append("")

    target_files = slice_record.front_matter.get("target_files")
    if target_files:
        lines.append("## Target files")
        lines.append("")
        for f in target_files:
            lines.append(f"- `{f}`")
        lines.append("")

    steps = slice_record.front_matter.get("implementation_steps")
    if steps:
        lines.append("## Implementation steps")
        lines.append("")
        for i, step in enumerate(steps, 1):
            lines.append(f"{i}. {step}")
        lines.append("")

    criteria = slice_record.front_matter.get("acceptance_criteria")
    if criteria:
        lines.append("## Acceptance criteria")
        lines.append("")
        for c in criteria:
            lines.append(f"- [ ] {c}")
        lines.append("")

    validation_cmds = slice_record.front_matter.get("validation_commands")
    if validation_cmds:
        lines.append("## Validation commands")
        lines.append("")
        for cmd in validation_cmds:
            lines.append("```bash")
            lines.append(cmd)
            lines.append("```")
            lines.append("")

    if decisions:
        lines.append("## Related decisions")
        lines.append("")
        for dec in decisions:
            status = dec.front_matter.get("status", "open")
            chosen = dec.front_matter.get("chosen_option", "none")
            dtype = dec.front_matter.get("decision_type", "")
            label = dec.front_matter.get("title", dec.record_id)
            lines.append(
                f"- {dec.record_id}: {label} [{status}] "
                f"(chosen: {chosen}, type: {dtype})"
            )
        lines.append("")

    if risks:
        lines.append("## Risks")
        lines.append("")
        for risk in risks:
            title = risk.front_matter.get("title", risk.record_id)
            impact = risk.front_matter.get("impact", "unknown")
            mitigation = risk.front_matter.get("mitigation", "")
            lines.append(f"- {title} (impact: {impact})")
            if mitigation:
                lines.append(f"  Mitigation: {mitigation}")
        lines.append("")

    return "\n".join(lines)
