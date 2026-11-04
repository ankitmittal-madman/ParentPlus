# ParentPlus Database Security Review


## Child creation database control — 2026-11-04

Draft migration 034 adds a private database switch that defaults off and gates direct authenticated `create_child` calls and retries. Existing behaviour tests explicitly enable it only in synthetic isolated fixtures; separate checks cover disabled/missing control, privileges and disable-versus-write ordering. A denied retry does not prove an earlier request failed. The parent-facing creation journey, durable lost-response recovery, real JWT/provider verification and lifecycle review remain incomplete. See [the child creation control spec](superpowers/specs/2026-11-04-child-creation-control.md).


## Child-creation replay safeguard — 2026-11-04

A local review reproduced an existing issue where replaying a child-creation request after the creator's guardianship was deleted recreated a provisional relationship, and replay after revocation or dispute still returned success. Draft migration 033 prevents that replay: an existing request requires a current provisional or active relationship before comparing details, and does not recreate one. Local tests cover deletion, revocation, dispute, both deletion/retry orderings and function privileges; see the current gate evidence.

The existing `create_child` function remains directly callable by authenticated database roles and is not controlled by the parent profile-read flag. This change does not implement a child-creation UI, durable recovery after a lost response, real JWT verification, lifecycle or retention policy. Do not treat this local safeguard as approval to use real child data or as proof of production readiness.

Status: Open
Milestone: M2 Authentication and Data Foundation
Migration: 20261101000100_identity_workspaces.sql

## Evidence reconciliation — 2026-11-03

The checklist and contract text below are retained as an open review. Historical
“not implemented/tested” labels must not be read as absence of the local migrations
and narrower scenario tests now indexed in [Quality Evidence](QUALITY_EVIDENCE.md)
and [the independent audit](INTELLIGENT_QUALITY_GATE_AUDIT.md).
A passing synthetic test does not close a broader lifecycle, privilege, real-JWT
or production-security guarantee. No checkbox is automatically marked complete;
review each claim against its exact evidence and unresolved product controls.

## 1. Workspace creation
- [ ] Only authenticated users can request workspace creation.
- [ ] Workspace and initial Owner membership are created atomically.
- [ ] Failed creation rolls back both records.
- [ ] A workspace cannot be left without an authorized active Owner.
- [ ] Duplicate requests cannot create unintended workspaces.

## 2. Role and membership security
- [ ] Coaches cannot promote themselves.
- [ ] Owners cannot be removed without a safe ownership-transfer process.
- [ ] Only authorized staff can invite or remove members.
- [ ] Suspended and removed members lose private workspace access.
- [ ] Membership status changes are auditable.

## 3. Row-Level Security
- [ ] Users can access only authorized private workspaces.
- [ ] Memberships cannot be queried across unrelated workspaces.
- [ ] Public discovery data is separated from private workspace data.
- [ ] Application users cannot bypass role checks through direct API calls.
- [ ] RLS policies are tested with multiple users and workspaces.
- [ ] Table privileges and privileged-role access are reviewed.

## 4. Identity and deletion
- [ ] Profile deletion behavior is reviewed.
- [ ] Historical records do not disappear unintentionally.
- [ ] Account deletion and privacy requirements are defined.
- [ ] Authentication identity and application profile remain separate.

## 5. Required negative tests
- [ ] Coach attempts to promote themselves to Owner.
- [ ] Coach attempts to access another workspace.
- [ ] Removed member attempts to read private records.
- [ ] Unauthenticated user attempts workspace creation.
- [ ] User attempts to modify another user's profile.
- [ ] Owner removal attempts to leave workspace without an Owner.

## 6. Migration readiness
- [ ] SQL syntax validated against a compatible PostgreSQL environment.
- [ ] Security policies implemented and tested.
- [ ] No real children's data used in testing.
- [ ] Founder reviews and approves deployment.

## 7. Initial RLS policy contract

### Profiles
- Authenticated users can read their own profile.
- Authenticated users can update permitted fields on their own profile.
- Users cannot directly change their profile ID.
- Profile creation requires a controlled onboarding mechanism.

### Workspaces
- Active workspace members can read their private workspace.
- Suspended and removed members cannot read private workspace data.
- Workspace creation uses the authorized create_workspace function.
- Direct workspace insertion, modification and deletion are denied to ordinary application users.

### Memberships
- Active users can read their own membership.
- Owners and administrators may eventually manage authorized memberships.
- Initial migration does not grant direct membership mutation.
- Role escalation and ownership transfer require separate trusted operations.
- No user may read unrelated workspace memberships.

### Workspace creation
- Only authenticated users may execute create_workspace.
- The function derives the creator from auth.uid().
- The request ID is required and scoped to the creator.
- Repeated requests must not create duplicate workspaces.
- Existing requests must not bypass current access restrictions.

### Testing requirements
- Verify access as multiple authenticated users.
- Verify unauthenticated access is denied.
- Verify suspended and removed membership behavior.
- Verify direct role escalation is denied.
- Verify cross-workspace reads and writes are denied.
- Verify function privileges and owner in the target environment.

Status: Proposed security contract; not implemented or tested.
