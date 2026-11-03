# ParentPlus Shared AI Communication Standard

Use this standard for updates, reviews and handoffs across ParentPlus assistants.
The existing CODEX_COMMUNICATION_STANDARD.md filename is retained for compatibility;
it is the single shared communication standard, not a Codex-only policy.
Write for the founder as an AI Product Manager: explain the outcome, its product
impact and the evidence in simple, clear English.

This document governs communication. The [engineering standards](ENGINEERING_STANDARDS.md)
and [feature delivery workflow](FEATURE_DELIVERY_WORKFLOW.md) remain the authority
for engineering, testing, security, approvals and Git checkpoints. Follow applicable
instruction precedence and task permissions; a reporting preference grants no new
authorization or exemption. Keep the existing Superpowers and nested Next.js guidance.

## Explain the work clearly

- Lead with the result, finding or decision that matters to the founder.
- Define technical terms when needed and connect details to observable behavior,
  product risk or a decision. Avoid unexplained jargon and unsupported assurances.
- Keep routine updates concise. Use lists or tables when they make comparisons,
  test outcomes or decisions easier to understand. Put lengthy detail in a linked
  repository report while keeping the chat summary understandable on its own.
- During substantial work, report meaningful findings, changed assumptions,
  blockers and the next verification step. Do not replace progress with terminal
  transcripts or repeated promises to continue.
- Execute authorized safe work using available tools. Ask focused questions only
  for missing information, decisions or permissions that affect progress; explain
  what the answer unblocks. Reuse authorization already given within its scope.

## Adaptive presentation — v2

Design each response around its purpose. Do not force every implementation,
verification or discussion into the same eight-section template. Preserve the
information needed for the decision, but vary the layout, sequence and detail.
A short verification can use an outcome, a compact result table, one explanation
and a next action; a milestone or architecture discussion may need more depth.

### Outcome-led opening and visual hierarchy

Make the important outcome, blocker or founder decision immediately visible.
Follow an important opening heading with a short italic summary explaining the
observed result and why it matters. Use actual step identifiers only when the
current plan, handoff or founder instruction establishes them:

**STEP [existing step identifier] — [CLEAR OUTCOME]**

When no applicable identifier exists, use a descriptive task/milestone heading.
Never invent a step number or reuse an unrelated historical one. Examples and
placeholders are presentation guidance, not real project steps or results.

Choose a status icon only when it helps readers scan the outcome:

| Icon | Meaning |
| --- | --- |
| ✅ | Verified success supported by evidence |
| ⚠️ | Warning, partial completion or remaining uncertainty |
| ❌ | Confirmed failure |
| 🔍 | Investigation |
| 🛠️ | Implementation work |
| 📋 | Planning |

Do not overuse icons, badges or decoration. Expected future success must not use
a verified-success label. State whether a result is local, hosted, partial or
pending; implementation completion does not imply tests, publication or release.

Use Markdown hierarchy intentionally where supported by the current client:
`#` for a major project/milestone title, `##` for important sections, `###` for
supporting subsections, and **inline labels** for small details. Do not give every
heading equal prominence. Use whitespace, short paragraphs, compact tables and
bold emphasis; keep technical depth without a dense wall of text.

### Choose content and layout by response purpose

These are adaptable patterns, not compulsory sections or a second fixed template.

| Response purpose | Useful content and presentation |
| --- | --- |
| Implementation completed | Outcome and italic summary; what changed and why; relevant quality evidence; incomplete work and next action |
| Verification passed | Concise result table, exact scope/counts, short implication and next action |
| Failure/debugging | Failed check and evidence; root cause or clearly labelled hypothesis; impact/safety; correction; retest evidence or plan |
| Architecture explanation | Simple mental model; component responsibilities and boundaries; diagram/flow; product example; dependencies and trade-offs |
| Product decision | Problem and options; evidence and trade-offs; recommendation; explicit decision/approval needed |
| Roadmap review | Milestone table with completed/current/next work, exit criteria, dependencies and unresolved risks |
| Security incident/risk | Observed facts, affected assets and boundaries, known/unknown impact, safe containment and required decisions; never expose secrets or personal data |
| Git checkpoint | Actual branch and commit; working-tree state; local/remote comparison with observation scope; deployment status |
| Development planning | Acceptance criteria, current slice, dependencies, test plan, risks and proposed sequence |
| Founder action required | The specific action, why it is needed, what the agent will do, the expected result and existing approval boundary |

For milestone/feature progress, use a table or checklist that suits the question.
Use Complete, Passed, In Progress, Next, Pending and Blocked consistently and state
the bounded scope. PASS/FAIL describe observed checks; PENDING is unverified or
awaiting action, and BLOCKED names a preventing prerequisite. Include only relevant
verification rows; do not mechanically include TypeScript, lint or build rows for
unrelated work. Show unrun relevant checks and their reasons explicitly.

Use a progress bar or percentage only with an objective denominator and evidence.
Never estimate milestone completion numerically from file counts or intuition.

### Narrative, next actions and expected outcomes

Start with the simplest useful mental model. Explain the problem, why it matters,
what changed or needs changing, how components interact, supporting engineering
evidence, the effect on ParentPlus and the logical next action. These are narrative
needs, not a mandatory seven-section outline. Use natural, simple Indian English.

Recommend one next action with its reason, scope, dependencies, what the agent
will do and what the founder needs to decide/do. Provide a complete copy-ready
command and expected result only when the founder genuinely must execute it.
Perform available authorized work directly instead of delegating routine terminal
work. A recommendation never expands existing permission.

If expected results help, label them as expected and separate them from observed
results. Use a compact table when it clarifies. Do not label a forecast PASS.
Explain the following milestone/dependencies when relevant, without resuming
unrelated feature development while this refinement awaits review.

### Diagrams and concrete explanations

Use Mermaid when a diagram materially improves understanding. Choose its type
according to the concept:

| Diagram | Suitable use |
| --- | --- |
| Flowchart | User journeys and processing flows |
| Sequence diagram | Interactions among actual frontend, API, backend and database participants |
| Architecture/block diagram | Major components and security boundaries |
| State diagram | Lifecycle states and transitions |
| Entity relationship diagram | Actual or explicitly proposed tables and relationships |
| Dependency graph | Milestone/implementation prerequisites |

Keep labels readable and complexity proportional. Explain the diagram in plain
English afterward and use a concrete ParentPlus example when helpful. Use only
real applicable components; proposed/hypothetical flows and synthetic people must
be labelled. Do not invent a backend, live integration, role or granted access to
fit an example. Keep connection, enrollment and sensitive access boundaries accurate.

### Rendering and tool limitations

Use native Markdown and Mermaid only to the extent supported by the current
client. Do not claim ChatGPT-specific cards, rich widgets, interactive progress
bars or other UI capabilities exist in Codex or Claude without evidence.
When rich UI is unavailable, preserve the hierarchy with supported text, tables
and diagrams. If Mermaid cannot be rendered, provide a readable text flow or
source and state the limitation; do not claim rendering was verified.

## Report evidence accurately

- Distinguish implemented, planned and deferred behavior; local validation, hosted
  CI and production behavior; and a selection plan from executed test evidence.
- State what actually ran, the observed outcome and where its evidence is stored.
  Keep passed, failed, skipped, expected-failure and unrun checks distinct. Explain
  relevant failures or unavailable checks instead of silently omitting them.
- Label historical results and reused evidence. When continuing existing work,
  inspect the current state and explain what was newly checked; do not describe an
  earlier run as a fresh execution or assume a new commit has passed hosted CI.
- Call a review independent only when a separate reviewer actually performed it.
  Classify findings by severity and explain impact, reproduction, correction and
  remaining uncertainty. A green existing suite alone does not resolve a defect.
- For gaps, state whether they are acceptable for the present scope, block the
  affected feature/release, or require a future decision. Name the condition that
  changes that disposition; do not present missing coverage as passing behavior.
- Describe automation or AI capabilities as active only when repository and
  execution evidence supports that claim. Separate prepared instructions from
  behavior that still depends on an invoked agent, tools, configuration or review.

## Structure a substantive engineering handoff

Choose the adaptive layout that fits the work. The following is a factual checklist
for substantive handoffs, not a mandatory section count or response template.
Integrate applicable facts into the chosen layout and never hide relevant gaps:

1. Main outcome and severity-ranked independent findings, when a review applies.
2. Changes made and why, with exact files or a linked exact diff/file inventory.
3. Checks executed and results, with evidence links and any failed or unrun checks.
4. Coverage gaps, remaining risks and practical limitations.
5. Updated standards or documentation, when applicable.
6. Future workflow or follow-up steps, distinguishing available from proposed behavior.
7. Current branch, commit and working-tree state, including whether changes are local.
8. Specific founder decisions or approvals needed next, within the existing rules.

Scale the report to the change. For documentation-only work, show the proposed
wording or exact patch, explain its purpose, verify references and diff scope, and
state what cannot be established without observing future sessions. Do not imply
application behavior was tested merely because documentation checks passed.

These are repository instructions, not a background service or a guarantee of
future agent compliance. New sessions must receive this repository version and
read the applicable guidance; actual behavior must be observed and reviewed.

## Cross-agent explanations and Technical Appendix

Use simple, natural Indian English: precise, professional and conversational.
Prefer wording such as “The output confirms that all six automated tests passed”
when six tests actually ran, or “Before changing the database, verify its current
migrations and authorisation rules.” Avoid elaborate phrases such as “a robust
cross-functional governance substrate.” Explain important choices from first
principles: the problem, why the chosen boundary or component is needed, and the
trade-off for the Product Manager. Use correct technical terms and define them;
do not replace precision with jargon or assume the founder is a developer.

Use structured Markdown headings and tables when useful for substantial reports.
Explain what was built and why, relevant system/data flows, test evidence,
quality status, PM implications, remaining risks and next steps. Scale detail to
the task; a routine status reply need not repeat a long engineering report.

For important unfamiliar concepts in substantial explanations, include a
Technical Appendix using this structure for each concept:

| Field | Explain |
| --- | --- |
| What it is | A plain-English definition |
| Why it is used | The problem it solves and key trade-off |
| Where it fits | The actual ParentPlus component or workflow, or clearly labelled proposal |
| PM mental model | A useful way to reason about its product consequence |
| Example | A concrete example consistent with current implementation status |

State the context actually available: checkout branch/commit/dirty scope, connector
view or supplied snapshot. Another assistant's statement is not proof that the
same branch, evidence or approval is visible here. Record useful conclusions and
decisions, not hidden reasoning or private chat transcripts. Use the shared
[project context](PROJECT_CONTEXT.md), [handoff](AGENT_HANDOFF.md) and
[quality-evidence index](QUALITY_EVIDENCE.md) rather than creating parallel memory
or communication documents. No connector or cross-agent synchronisation is
installed by these instructions.
