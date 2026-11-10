# Browser-accessible founder testing

Latest founder instruction (2026-11-10) supersedes the earlier separate-backend
proposal: use EXISTING Supabase project fmavpazczahxeusqbxuh, which is explicitly a
testing project, and deploy the Vercel app for testing. Dummy .test email/code123456
must work on the deployed app; launch authentication is a later explicit instruction.
No new account/project, paid service, database reset or deletion of existing records.
Preserve all earlier uncommitted recovery/first-use/founder work.

A production Next.js build is not a product launch. On Vercel, non-secret checked-in
founder-testing.config.json enables implemented features and dummy sign-in unless
an explicit launch-stage build is requested. Server-only runtime service credentials
remain Vercel environment variables and are never compiled into the public defaults.
The selected backend URL/project reference must match, and local development remains
supported. Ordinary persona RPC/RLS checks remain; founder controls override test
membership states. No real email delivery or identity verification is required.

The management API verified001–013, then atomically applied missing014–049 with
history receipts after a successful synthetic upgrade rehearsal. Original row
fingerprints for eight application tables plus Auth accounts were preserved. The
four implemented-feature controls were enabled. No Auth provider configuration
change or data reset was necessary.

Use the existing GitHub→Vercel route, not an unavailable Vercel integration. The
founder explicitly authorised deployment. The only Vercel account step is supplying
PARENTPLUS_TEST_SERVICE_KEY (or existing SUPABASE_SERVICE_ROLE_KEY) in Preview and
Production. Never request the value in chat. Review/check the complete build before
publishing; inspect actual deployment status and distinguish hosted verification
from local evidence. Enrollment/attendance/diary/fees remain separate incomplete work.
