# ParentPlus — Claude entrypoint

At task start, explicitly read the repository
[Superpowers bootstrap](.agents/skills/using-superpowers/SKILL.md) and its
[Claude tool adapter](.agents/skills/using-superpowers/references/claude-code-tools.md).
Apply relevant skills using only tools actually available. This explicit reading
path does not assume a separately installed Claude plugin or automatic discovery.

Then read [Project Context](docs/PROJECT_CONTEXT.md) and the latest
[Agent Handoff](docs/AGENT_HANDOFF.md). Use their reading order and ownership map.
Read the shared [engineering standards](docs/ENGINEERING_STANDARDS.md),
[delivery workflow](docs/FEATURE_DELIVERY_WORKFLOW.md) and
[communication standard](docs/CODEX_COMMUNICATION_STANDARD.md).

Before edits, report the actual repository/snapshot state, the existing work you
must preserve and the requested next step. Existing task permissions and approval
boundaries apply; this entrypoint grants no additional authority.

Preserve applicable nested AGENTS.md constraints, including
[the web application's Next.js instructions](apps/web/AGENTS.md).
Repository Superpowers guidance is described in [docs/superpowers.md](docs/superpowers.md).
Use only skills, adapters and tools supported by the actual Claude environment;
do not assume Codex-specific tool names, subagents or integrations are available.
No global Claude configuration or connector is installed by this file.
