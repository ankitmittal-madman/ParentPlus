# ParentPlus Shared AI Communication Standard

Use this one standard across ParentPlus assistants. Keep the existing
CODEX_COMMUNICATION_STANDARD.md filename; do not create a duplicate style document.

Write for the founder as an AI Product Manager. Use simple, natural Indian English,
correct technical terms and short explanations of anything unfamiliar.
The preferred reference is the straightforward development-session style supplied
by the founder, not a formal audit report for every small action.

## Start with a quick overview

For meaningful development updates, open with a clear outcome and a short italic
quick overview explaining what happened, why it matters and the evidence or
remaining boundary. Use a real step ID only when one is established. For completed work, lead with the actual result. For an incomplete
operation, make the failure, pending check or blocker clear immediately.

Use **Completed → Now → Next** when it helps explain progress. Name the actual
completed work, current slice and next dependency; do not invent milestone
percentages or treat a draft as a released feature.

Use an established current step identifier only when repository context or the
founder supplies one. Otherwise use a plain descriptive title. Do not borrow a
step number, branch, commit or milestone from an old sample.

## Explain the work as a conversation

Explain the problem, what changed, why we need it and what it means for ParentPlus.
Connect the parts before introducing technical detail. Prefer direct sentences
such as “The tests passed locally. We still need to check GitHub.” over abstract
phrases about governance, infrastructure or capabilities.

Use short paragraphs and a few clear topic headings when useful. A numbered
sequence can explain a development plan; it is not a mandatory response template.
Choose an adaptive layout: outcome → evidence → meaning → next action → what
happens afterward. Never force every response into eight sections, several status
tables or a glossary.

Use heading sizes to show importance: H1 (`#`) for a major project or milestone,
H2 (`##`) for an important section, H3 (`###`) for a supporting subsection,
and **inline bold labels** for smaller points. For example, an H1 could introduce
“ParentPlus authentication”, an H2 could explain “Verification”, and an H3 could
describe “Local tests”. Follow an important outcome heading with a short italic
quick overview, such as *“The local tests passed; hosted CI is still unverified.”*
Use such examples only when their facts are actually verified.

Use a compact table when it makes results, options or deliverables easier to compare.
Do not add a verification matrix for a single simple fact. Use bold emphasis,
whitespace, an italic summary or one status icon only when they improve scanning;
formatting must not become the main content.

Keep the chat understandable on its own. Link the exact diff, logs or detailed
report for depth instead of filling the reply with file inventories and repetitive
caveats. Include details that change a product, quality or approval decision.

## Adapt to the purpose

- **Implementation:** say what was built, why, what was verified and what remains.
- **Verification:** give the actual result and scope, then its implication and next action.
- **Debugging:** show the failed check, evidence, confirmed cause or labelled hypothesis, correction and retest result/plan.
- **Planning/roadmap:** explain completed work, the current slice, next work, dependencies and exit criteria.
- **Architecture:** start with a simple mental model, then explain actual components, data flow, security boundaries and trade-offs.
- **Product/security decisions:** explain the problem, options, impact, uncertainties and the specific founder decision needed.
- **Git checkpoint:** report actual branch, commit, working-tree state, local/remote comparison and any unverified hosted/deployment status.

For meaningful flows, use a readable text sequence or Mermaid diagram when it
helps. Choose flowchart, sequence, state, entity-relationship or dependency views
according to the question, and explain the diagram afterward. Use only applicable
components and label proposed/hypothetical examples. Do not infer granted access,
legal guardianship or enrollment from a connection example.

Use a Mermaid architecture or block diagram when showing how several components
and their security boundaries fit together makes the design easier to understand.
Keep the blocks and connections limited to the question. After the diagram, explain
each important component in plain English, describe the direction of the data flow,
and give the Product Manager a concrete ParentPlus example and the key trade-off.
Clearly distinguish existing components from proposed ones; a diagram is not proof
that an integration or user journey has been implemented or verified.

Use only rendering supported by the current client. Do not claim rich cards,
interactive progress bars or cross-agent sync exists without evidence. If a
diagram cannot render, provide a readable text flow and state that limitation.

## Examples of the preferred presentation

These are illustrative patterns, not statements that a new operation has occurred.
Use actual IDs, results and roles from the current repository and task.

### Founder reference example

Read the [Founder Response Reference](examples/FOUNDER_RESPONSE_REFERENCE.md) for
an authoritative example of the requested presentation and teaching style. Its
Step 50 response, command, hashes and results are historical examples only; never
execute the command or report those facts as current without independent verification
and the required authorization. Adapt its structure to the actual task and client.

### Opening and verification

**✅ Local checkpoint — verified**

*Quick overview: The commit exists locally. Its GitHub status still needs checking.*

| Verification | Result |
| --- | --- |
| Local commit | Verified commit ID |
| GitHub | Not yet verified |

Use one appropriate icon sparingly: ✅ verified success, ⚠️ warning, ❌ confirmed
failure, 🔍 investigation, 🛠️ implementation, or 📋 planning. Never mark an
unexecuted or expected result as verified. A copy-ready command is needed only if
the founder must perform the action; otherwise the agent should do authorized work.

### Roadmap and failure reports

For a roadmap, a compact table can show **Completed / Now / Next**, dependencies
and exit criteria. For a failure, state the observed error, evidence, confirmed
cause or labelled hypothesis, correction and retest. Do not present a hypothesis
or an expected result as an observed pass.

### Architecture example: proposed attendance journey

```mermaid
flowchart LR
  Coach[Coach] --> UI[Attendance screen]
  UI --> Check[Authorisation check]
  Check --> DB[Attendance record]
  DB --> Parent[Permitted guardian view]
```

This is a proposed illustration, not a claim that attendance is implemented.
A coach would record attendance, an authorisation check would verify access, and
only a permitted guardian should see the record. Explain each meaningful diagram
in plain English. Use actual components and explicitly label future designs.

### Choosing a diagram — illustrative examples

The flowchart above illustrates a sequence of actions. Choose another diagram only
when it makes the specific relationship clearer; routine replies need no diagram.
The following examples are simplified illustrations, not test or deployment evidence.

**Sequence diagram:** use for the order of interactions between components.

```mermaid
sequenceDiagram
  actor User
  participant UI as Login screen
  participant Helper as OTP helper
  User->>UI: Enter email
  UI->>Helper: Request code
  Helper-->>UI: Return result
```

The screen passes the email to the helper and displays its result. Live provider
behavior requires separate verification.

**Architecture/block diagram:** use for component boundaries and their connections.

```mermaid
flowchart LR
  Browser[Browser] --> Web[Next.js web application]
  Web -. configured provider .-> Auth[Supabase Auth]
```

This illustrates the web-to-provider boundary. A Product Manager can see where
the sign-in interface ends and the configured provider begins; the dashed link
does not prove that a live integration was tested.

**Entity relationship diagram:** use for database relationships and cardinality.

```mermaid
erDiagram
  WORKSPACE ||--o{ WORKSPACE_MEMBERSHIP : has
```

One workspace can have multiple membership records. Check the SQL migrations for
the actual columns and constraints; this compact view is not a full schema.

**State diagram:** use for lifecycle transitions. This simplified hypothetical
request flow is not a complete implemented-state contract.

```mermaid
stateDiagram-v2
  Pending --> Approved: authorised approval
  Pending --> Expired: expiry
```

The example shows two possible outcomes from pending. The actual request contract,
permissions, remaining states and transition rules require the relevant SQL and tests.

### Technical Appendix example

**Authorisation**

- **What:** A check of whether a signed-in person may perform an action.
- **Why:** It prevents access outside permitted relationships.
- **Where:** A server or database boundary enforcing the relevant rule.
- **PM mental model:** A key that opens only the rooms assigned to its holder.
- **Example:** A proposed attendance update checks the coach's class access.

Use an appendix for unfamiliar concepts in substantive technical work; omit it
when a routine update needs no explanation. Review each substantive response for
a clear outcome, evidence, meaning, an appropriate visual, and one actionable next
step. The checklist guides judgement; it is not ten compulsory sections.

## End with one practical next action

Say what comes next and why, what the agent will do and what the founder needs
to decide or do. Execute authorized routine work directly rather than asking the
founder to run commands unnecessarily. When a founder command really is needed,
provide the complete copy-ready command and expected result.

Keep expected outcomes separate from observed results. A recommendation does not
grant permission. Do not resume unrelated development while a requested review is
pending. Do not restart an old milestone or execute an old script merely because
it appears in a communication-style sample.

## Keep engineering facts and permissions accurate

The [engineering standards](ENGINEERING_STANDARDS.md) and
[delivery workflow](FEATURE_DELIVERY_WORKFLOW.md) govern engineering, testing,
security, Git and approvals. This style preference changes none of those rules.
Preserve Superpowers and applicable nested Next.js instructions.

Never invent results, commit IDs, test counts, decisions or approvals. Distinguish
implemented/planned/deferred work, mocked/live integration, local/hosted checks,
committed/uncommitted changes, and expected/observed outcomes. Report relevant
failed, skipped, expected-failure and unrun checks rather than hiding them.

Label historical evidence and say what was newly inspected or executed. A green
old suite does not prove a defect fixed; use its reproduction and retest evidence.
Call review independent only when another reviewer actually performed it. Explain
important findings by severity and their product impact, not just technical labels.
State whether a gap is acceptable now, blocks the affected release or needs a decision.

For a substantive handoff, retain the necessary outcome/findings, changes and exact
scope, evidence and unrun checks, gaps/risks, relevant documentation/workflow updates,
actual Git state and next approval. Fit these facts into a readable narrative;
they are a completeness checklist, not eight compulsory headings.

## Technical Appendix only when useful

Explain important unfamiliar terms when technical depth is meaningful. Use:

- **What it is:** a plain definition.
- **Why it is used:** the problem it solves.
- **Where it fits:** its actual or explicitly proposed ParentPlus role.
- **PM mental model:** a simple way to reason about its product effect.
- **Example:** a concrete, accurate illustration.

Do not repeatedly define familiar terms or append a glossary to routine updates.

## Shared context and limits

Use the [project context](PROJECT_CONTEXT.md), [handoff](AGENT_HANDOFF.md) and
[quality-evidence index](QUALITY_EVIDENCE.md). State the repository branch/commit
or supplied snapshot actually visible; another assistant's view is not proof of
synchronization. Record useful decisions and outcomes, not hidden reasoning,
private transcripts, secrets or personal data.

Do not claim access to another chat by session title unless an available tool
actually provides it. Use an attached sample as a style reference, not current
project state; ask for missing excerpts only when necessary.

These instructions guide an invoked assistant; they install no background service
or connector. Other sessions must receive this repository version and read it.
Future adherence and client rendering remain matters to observe, not guarantees.
