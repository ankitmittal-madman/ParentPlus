# Superpowers for ParentPlus

ParentPlus includes the 15 [Superpowers](https://github.com/obra/superpowers) skills
under `.agents/skills/`, where Codex discovers repository skills automatically.
This is a repository-scoped skill installation, not a global plugin installation.

## Use in Codex

1. Open or clone this repository and start Codex from its root.
2. Start a new turn; if skills do not appear, restart Codex.
3. In Codex CLI or the IDE extension, use `/skills` to inspect the installed skills.

You can request a skill explicitly, for example:

- `$brainstorming Help design the ParentPlus onboarding flow.`
- `$writing-plans Plan the agreed onboarding implementation.`
- `$systematic-debugging Investigate this failing test.`
- `$verification-before-completion Verify the changes before finishing.`

Skills also activate when a task matches their descriptions. `AGENTS.md` points
Codex to the bootstrap skill. No API keys or setup command are required.

Parallel-agent workflows depend on the tools and permissions available in your
Codex environment; follow the included Codex adaptation reference when supported.
The optional visual brainstorming companion needs Node.js. Graph rendering in
the skill-authoring workflow needs Graphviz. These tools are not required just
to load the skills.

## Source and updates

- Upstream: https://github.com/obra/superpowers
- Version: 7.0.1
- Pinned revision: `2ce8aa15d05bd57213e6f746f953aafb7ded7a8b`
- Upstream skill files and supporting resources are copied unchanged.
- License: MIT; see [SUPERPOWERS-LICENSE](SUPERPOWERS-LICENSE).

To update, review an upstream revision, replace the complete contents of the
15 skill directories with that revision's `skills/` contents, preserve executable
file modes, update the license and this revision, and verify the snapshot.
Keep project-specific instructions in `AGENTS.md` rather than editing upstream
skill files. Avoid installing the same skills globally as well, since Codex may
show duplicate skill names.

References:
- [OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills)
- [Upstream Superpowers installation](https://github.com/obra/superpowers#installation)
