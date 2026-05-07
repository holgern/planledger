from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_skill_md_exists():
    skill_path = REPO_ROOT / "skills" / "planledger" / "SKILL.md"
    assert skill_path.exists(), f"Missing skill file: {skill_path}"


def test_skill_md_contains_bundle_reference():
    content = (REPO_ROOT / "skills" / "planledger" / "SKILL.md").read_text()
    assert "planledger.plan_bundle.v1" in content


def test_skill_md_contains_workflow():
    content = (REPO_ROOT / "skills" / "planledger" / "SKILL.md").read_text()
    assert "Default workflow" in content


def test_readme_exists():
    readme_path = REPO_ROOT / "skills" / "planledger" / "README.md"
    assert readme_path.exists(), f"Missing readme: {readme_path}"


def test_readme_mentions_install_path():
    content = (REPO_ROOT / "skills" / "planledger" / "README.md").read_text()
    assert "~/.agents/skills" in content


def test_skill_not_inside_python_package():
    skill_in_pkg = REPO_ROOT / "planledger" / "skill"
    assert not skill_in_pkg.exists(), "Skill should not be inside the Python package"


def test_no_skill_cli_command():
    """The skill is not a Python module inside planledger package."""
    skill_module = REPO_ROOT / "planledger" / "skill.py"
    skill_dir = REPO_ROOT / "planledger" / "skill"
    assert not skill_module.exists()
    assert not skill_dir.exists()
