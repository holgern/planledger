from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_readme_describes_plan_only_product() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "structured, versioned implementation plans" in readme
    assert "not a task manager" in readme
    assert "rendered Markdown" in readme
    assert "goal create" not in readme
    assert "taskledger push-plan" not in readme


def test_skill_describes_plan_only_workflow() -> None:
    skill = (REPO_ROOT / "skills" / "planledger" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "create a new independent plan" in skill.lower()
    assert "Do not create goals, milestones, slices, or taskledger tasks." in skill
    assert "rendered Markdown path" in skill
    assert "snapshot export" not in skill
