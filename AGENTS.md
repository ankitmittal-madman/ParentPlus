# ParentPlus — Codex instructions

## Superpowers

This repository includes Superpowers skills in `.agents/skills/`.

At the start of a task, read `.agents/skills/using-superpowers/SKILL.md` and its
`references/codex-tools.md` reference, then use the skills relevant to the task.
Resolve skill resources relative to the skill directory.

Use brainstorming for new product work, planning for agreed multi-step work,
test-driven development for implementation, systematic debugging for failures,
and verification before claiming completion. Follow the code review and branch
completion workflows when relevant.

User instructions and environment permissions take precedence over these skills.
Use only tools, models, and capabilities actually available in the current
session. Do not change machine-wide Codex settings as part of ordinary project
work.

Installation details, examples, source revision, and update instructions are in
`docs/superpowers.md`.

## Engineering operating system

Before feature work, audits or quality-gate changes, read
`docs/ENGINEERING_STANDARDS.md` and follow
`docs/FEATURE_DELIVERY_WORKFLOW.md`. Update `docs/BUILD_PROGRESS.md` when verified
capabilities or milestone status changes. Keep requirements and executable test
references in `quality/requirements.json` truthful and current.

Use independent review and deterministic evidence; do not equate mocked/local
checks with real-provider, hosted CI or production validation. Preserve the
existing Superpowers and application-specific Next.js instructions.

Present the complete reviewed change scope, evidence and remaining risks before
requesting approval to commit. Do not commit until that approval is given.
Commit approval does not authorize push, merge, deployment, hosted migrations,
production access, repository-setting changes or paid services. Current task
instructions and existing explicit authorization take precedence over historical
roadmap checkpoint guidance. Use the existing isolated cloud checkout; do not
create a worktree unless explicitly requested.
