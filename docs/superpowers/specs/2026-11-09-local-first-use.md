# Real local first-use journeys

Reconciled base: `010fd412d034f3e8e7545c235b824e9e6ac36bdb`, recovered by
fast-forward after inspection. The supplied seven-file recovery patch is retained.
All development and testing is synthetic and local; no hosted Supabase operation.

Parent acceptance: explicit signup, invalid-code rejection, real Mailpit OTP,
child creation, reload recovery/confirmation, own-profile listing, unrelated-user
isolation and sign-out. Coach acceptance: signup, no-membership gate, create an
independent/academy workspace, create a weekly course/batch/session series,
reload recovery, acknowledge without duplication, and lose access on suspension.

Workspace onboarding uses the existing `create_workspace` controlled RPC and RLS
reads. No new database grants or migrations. Server and database controls remain
default off. Each action verifies Auth identity; expected actor and known request
key cannot confer access. A browser marker stores only version, actor ID and
request ID before a write. Recovery returns only currently accessible matching
workspace IDs. Empty status is explicitly unknown and never proves failure;
retry uses the same key. The marker is retained after success and on sign-out;
invalid/unavailable storage or another actor's marker blocks creation. The form
cannot create again after a known result. No global one-workspace-per-account
claim: workspaces intentionally support multiple memberships, and cross-device
lost-key discovery remains separate. Account changes invalidate visible results.

Browser tests restrict outbound requests to local app/API origins, and fixture SQL
uses only the fixed local Docker socket/container. No service key enters the app.
Temporarily enabled local controls are restored. Synthetic test rows are retained
for inspection; no reset or deletion of existing work is permitted.
