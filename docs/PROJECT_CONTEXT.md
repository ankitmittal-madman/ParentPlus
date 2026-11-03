# ParentPlus — Shared Project Context

This is the shared starting point for Codex, Claude Code, ChatGPT, ChatGPT Work
and other assistants. It indexes the authoritative documents; it is not a second
roadmap, schema, evidence ledger or record of private conversations.

GitHub is the intended durable store for reviewed and published project context.
Local commits and drafts are not automatically visible there. Every reader must
identify the branch/commit or explicitly supplied snapshot it can actually access.

## Product purpose and personas

ParentPlus is a parent companion platform for parents/guardians, independent
coaches and academies. Its intended product connects authorised family and
workspace relationships with learning delivery and communication.

| Persona | Intended need | Important boundary |
| --- | --- | --- |
| Parent/guardian | Access permitted information about their child's learning across providers | Authentication is not proof of legal guardianship or unrestricted access |
| Independent coach | Operate a single-member coaching workspace and support learners | Access is limited to authorised workspace/child relationships |
| Academy staff/owner | Coordinate shared staff, learning operations and family relationships | Roles are scoped per workspace, including coaches in multiple workspaces |

The intended product is broader than the current local foundation. See
[Build Progress](BUILD_PROGRESS.md) for implementation status and
[the roadmap](DEVELOPMENT_ROADMAP.md) for product milestones. Do not infer that a
listed persona journey, database concept or planned screen is functional.

## Confirmed principles and open scope

The [decision log](DECISION_LOG.md) owns the decision history. Confirmed directions
include email-first OTP, shared workspaces, multi-workspace membership, a shared
child identity, guardian-controlled linking and separate connection/enrollment
lifecycles. Two-way initiation is a product direction, not a claim both user
journeys are complete. Phone OTP and formal guardian-verification methods have
explicit deferrals; a declaration must never be labelled verified legal guardianship.

Children's privacy, tenant isolation, controlled authorisation and synthetic-only
local testing constrain development. Retention, disputes, sensitive access and
real-data rollout need the unresolved decisions and controls documented in the
architecture/security material. Do not invent product or privacy decisions to
fill gaps. Feature acceptance criteria belong in the relevant dated spec/plan.

## Canonical ownership and reading order

After the applicable root entrypoint (`AGENTS.md` for Codex or `CLAUDE.md` for
Claude Code), read this context, the handoff and the shared working standards.
Then read task-relevant detail from this map. Web changes also require the nested
[Next.js guidance](../apps/web/AGENTS.md).

| Information | Canonical owner | Read/update rule |
| --- | --- | --- |
| Product purpose and document map | This file | Change when product framing or document ownership changes |
| Session state, observed Git/snapshot, unfinished work, next action | [Agent Handoff](AGENT_HANDOFF.md) | Read at start; update after a meaningful session |
| Milestone-level implementation progress | [Build Progress](BUILD_PROGRESS.md) | Update after verified feature slices; do not copy live Git status here |
| Product milestones and exit criteria | [Development Roadmap](DEVELOPMENT_ROADMAP.md) | Change when scope, dependencies or milestone status changes |
| Decisions and rationale | [Decision Log](DECISION_LOG.md) | Add/annotate significant decisions; preserve history |
| Components, runtime boundaries and data flows | [System Architecture](SYSTEM_ARCHITECTURE.md) | Update when those boundaries change |
| Database contracts and planned domains | [Database Architecture](DATABASE_ARCHITECTURE.md) | Exact executable definitions remain in SQL migrations |
| Unresolved security review | [Database Security Review](DB_SECURITY_REVIEW.md) | Evidence for one scenario does not close a broader checklist item |
| Engineering, testing, approval and Git rules | [Engineering Standards](ENGINEERING_STANDARDS.md) | Preserve as the common engineering authority |
| Delivery steps and documentation maintenance | [Feature Delivery Workflow](FEATURE_DELIVERY_WORKFLOW.md) | Follow during implementation and handoff |
| Shared response style and Technical Appendix | [Communication Standard](CODEX_COMMUNICATION_STANDARD.md) | Keep this existing filename; do not create a parallel AI style document |
| Verification provenance, result availability and known limits | [Quality Evidence](QUALITY_EVIDENCE.md) | Update after quality checks; link detailed reports instead of copying them |
| Gate operation and exact scenario mappings | [Gate Guide](INTELLIGENT_QUALITY_GATE.md), [requirements registry](../quality/requirements.json) | Registry scenarios must remain truthful and executable |
| Skill installation and adapters | [Superpowers](superpowers.md) | Use only capabilities actually available to the current tool |

## How different assistants access the same context

| Assistant | Access route | What must be stated |
| --- | --- | --- |
| Codex | Checkout and root AGENTS.md | Actual branch, HEAD and dirty scope |
| Claude Code | Checkout and CLAUDE.md | Actual checkout state and supported tools |
| ChatGPT / ChatGPT Work | Explicitly configured repository access, or supplied documents | Which branch/commit or snapshot is visible; missing access stays unknown |
| Claude web / other chat tools | Supported integration or uploaded context | Snapshot provenance and anything unavailable |

No connector, background sync service or transfer of hidden reasoning is installed.
For a supplied context bundle, include these canonical documents, preparation date,
source branch/base commit, dirty scope and known omissions. Exclude credentials,
children's personal data and private conversation transcripts. A bundle containing
local drafts must say so; it is not the GitHub-published state.

## Reconciliation and concurrent work

Compare the handoff's preparation baseline with actual Git/snapshot evidence.
Documents are dated records, not permission to overwrite a different branch or
working tree. If facts differ, report the difference, preserve both scopes and
reconcile using source and verification evidence. Approval cannot be inferred
from a commit, a green check or another assistant's assumption.

Use one coordinated writer for overlapping files. Record intended file ownership,
check current content before patching and stop on unexpected concurrent changes.
The handoff is not a live lock. Compare-before-write checks and final diff review
help detect stale writes but cannot guarantee exclusion of an unrelated tool.
Technical locking for automated writers is a proposed follow-up, not active here.
