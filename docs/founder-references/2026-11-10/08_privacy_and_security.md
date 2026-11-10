# 08. Privacy and security

**In short:** we handle young children's names, photos and routines, and parents' trust is everything. Privacy is built into the database, not bolted on. This checklist is reviewed at every gate. It is not legal advice: have a lawyer review the privacy policy and consent wording before Stage 7.

## Children's data: our rules

1. **Collect the minimum.** First name, optional date of birth, the class. No school, no address, no health data in the pilot (health notes come later, in a separate restricted table).
2. **Verifiable parental consent** (India's DPDP Act 2023) before any photo, video or audio. Consent is specific (photo, video, audio, group photos, promotion), recorded with a policy version, append-only, and can be withdrawn at any time, with immediate effect (tests T46 to T51).
3. **No tracking or behavioural monitoring of children, and no advertising aimed at them** (the DPDP Act restricts both). Analytics describe coach and parent actions only. Session replay stays off, or fully masked.
4. **Private media.** Private storage bucket; links expire in 1 hour or less; parents see only what the consent rules allow.
5. **AI with names removed.** Names and phone numbers are swapped for placeholders before any AI call. Photos and audio of children are never sent to AI vendors by default. Voice notes are the coach's own speech; the coach is told that the speech service processes audio.
6. **Retention.** Media is kept for 90 days, unless it's saved to memories. Accounts and data are deleted on request within 30 days. Backups expire after 14 days.
7. **Breach response.** If personal data may have leaked: contain it, assess it, and inform affected families and the authorities as the law requires. Owner: the founder (decision D7), with the AI co-founder preparing the facts within 24 hours.

Check the latest DPDP Rules with a lawyer before launch. The rules and their timelines may have changed.

## Security basics

| Area | Rule |
|---|---|
| Accounts | Two-step login on every account (Google, GitHub, Supabase, Vercel, PostHog, Resend); a password manager for everything |
| Access rules | RLS on every table; tests for both "can" and "cannot" |
| Keys | Service-role and AI keys server-side only; never in the browser, code, chat or screenshots |
| Input | Validated with zod on the server; text length limits in the database |
| Uploads | Type and size checked; images re-encoded on the device; storage paths not guessable |
| Sessions | Supabase Auth defaults; sign out everywhere available |
| Dependencies | Weekly Dependabot; security fixes within 7 days |
| Admin access | No direct production edits; changes only through reviewed migrations |
| Audit | Important actions logged to `events` (who, what, when; no free text about children) |

## Gate checklist (copy into each gate review)

- [ ] No new personal data collected without an updated privacy note
- [ ] New tables have RLS and tests
- [ ] No children's data in analytics, logs or error reports (spot-check)
- [ ] Media links expire; consent withdrawal tested
- [ ] AI calls carry no names (log spot-check)
- [ ] Secrets are scanned (GitHub secret scanning is on)
- [ ] Backup restore drill passed
