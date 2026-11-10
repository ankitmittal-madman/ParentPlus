# Founder reference documents — received 10 November 2026

These 18 original attachments are preserved byte-for-byte. `manifest.json`
records their sizes and SHA-256 fingerprints. This date is the receipt date;
versions/dates inside the originals remain unchanged.

## Reading order

- [Working agreement](00_working_agreement.md), [pilot PRD](01_pilot_prd.md),
  [roadmap and gates](02_roadmap_and_gates.md), [Stage 1–2 stories](10_backlog_stage1_stage2.md).
- [Architecture](03_architecture.md), [data model](04_data_model.md),
  [parent items contract](05_parent_items_contract.md).
- [Engineering](06_engineering_standards.md), [ready/done](07_definition_of_ready_and_done.md),
  [privacy](08_privacy_and_security.md), [founder preparation](09_founder_prep_checklist.md),
  [launch checklist](11_launch_readiness_checklist.md), [risks](12_risk_register.md),
  [build diary template](13_build_diary_template.md), [decisions](14_decision_log.md).
- [Coach design prototype](ParentPlus_Coach_Tutor_App.html),
  [Class Diary feature reference](Parent_Plus_Module2_Class_Diary_v0.2.html),
  [build journey](Parent_Plus_Build_Journey.html).

Download an HTML file and open it in a browser to use the prototype. GitHub's
source page does not run an HTML app. Prototype records and button demonstrations
are illustrative; they do not prove database integration or delivered features.

## Applying the references to the current build

The founder requested preservation and alignment, not execution of commands or
account actions contained in these attachments. Current explicit task instructions,
repository engineering rules and subsequently confirmed product decisions govern
implementation. These documents add no deployment, spending or account permission.

- Continue the existing Next.js/Supabase application and append-only migrations;
  do not replace the current workspace/course/batch schema with the older
  organisation/class proposal. Map concepts deliberately.
- The existing hosted Supabase project is founder testing only, as confirmed in
  this conversation. Keep dummy `.test` email / `123456` OTP and real database
  persistence. The older Google/email-provider and separate-production instructions
  are launch/reference plans, not requirements to interrupt founder testing.
- Prioritise class setup, family connections and the student directory before fees.
  Joining an academy and enrolment in a batch remain separate explicit actions
  under the current decision log. An invitation does not establish verified legal
  guardianship or consent for media/pickup/fees.
- Preserve current lifecycle and privacy decisions. The older trial/paused/left
  terminology and numeric retention proposals need explicit reconciliation before
  implementing those behaviours; they do not silently replace current contracts.
- Treat stage checklists, tests and prototype data as requirements, not passed
  gates. Current delivery and evidence live in the canonical documents below.

[Project context](../../PROJECT_CONTEXT.md) · [Build progress](../../BUILD_PROGRESS.md) ·
[Decisions](../../DECISION_LOG.md) · [Quality evidence](../../QUALITY_EVIDENCE.md)

## What the e2e folders mean

**End-to-end (E2E)** tests operate a browser through user journeys. They click
buttons, fill forms and verify what appears. Some suites use isolated fixtures;
others connect to real local Supabase. Only the latter establish a local
browser-to-database journey. Neither automatically proves hosted behaviour.

The reusable founder QA workflow also produces an HTML scenario/result report,
screenshots and an Excel workbook. New scenarios must be registered and actually
run; adding a scenario is not a passing result. See [automated testing](../../BROWSER_TESTING.md).
