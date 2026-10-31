# ParentPlus Database Security Review

Status: Open
Milestone: M2 Authentication and Data Foundation
Migration: 20261101000100_identity_workspaces.sql

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
