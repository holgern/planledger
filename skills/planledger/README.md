# Planledger Agent Skill

This skill teaches a coding harness how to use planledger as a plan-only CLI for structured, versioned implementation handoffs.

## Installation

```bash
mkdir -p ~/.agents/skills
cp -R ./skills/planledger ~/.agents/skills/planledger
```

## What this skill covers

- creating a new independent plan for each new planning request unless the user names an existing plan id;
- updating focused plan components instead of rewriting unrelated sections;
- building the latest rendered Markdown handoff after changes;
- setting plan status to `done` only when the human approves the plan.
