# 01. Product requirements: Pilot v1

**In short:** Pilot v1 proves one promise with one academy. After every class, parents hear what their child did within an hour, and it costs the coach under 2 minutes. Fees come only after the daily habit is proven.

## 1. Problem

Society coaches teach children aged 3 to 7 with no tools. Attendance, updates, photos and reminders live in their heads and in WhatsApp, and compete with teaching. Parents can't see what their child is learning. (Full reasoning: Module 2 v0.2 spec.)

## 2. Who the pilot is for

- **One academy** (decision D8), 1 to 3 coaches, 20 to 30 families. Demo data: FitKids Gym, Vashi; Coach Vikram; parent Manu; child Rudraansh.
- Coach persona: busy and phone-only, possibly teaching back-to-back batches; comfortable in Hinglish.
- Parent persona: wants to know what the child did, that they're safe, and to keep memories; doesn't want spam.

## 3. Scope

### In Pilot v1 (Stages 1 to 6)

| Area | Features (Module 2 IDs) |
|---|---|
| Foundation | Sign-in, profiles, academy creation, PWA, English and Hindi, typed-item contract (M2-58), event log (M2-46), free-tier adapters (M2-45) |
| Class setup | Batches and recurring sessions (M2-01), guardians and invite links (M2-02), student list (M2-49) |
| Attendance | Parent signals (M2-06), fast attendance (M2-09), Today list (M2-41) |
| Updates and moments | Class updates with preview (M2-13, M2-16), personal notes (M2-20), consent (M2-25), capture (M2-26), safe sharing (M2-27), try-at-home (M2-47), milestone moments (M2-48), announcements (M2-50) |
| AI assist | Voice to update (M2-14), AI engine (M2-37), name removal (M2-38), spotlight and observations (M2-18, M2-19) |
| Reminders | Outbox and channels (M2-40), get-ready reminder (M2-04), schedule changes with RSVP (M2-05) |

### Out of Pilot v1 (later stages)

Fees (Stage 9, after the pilot gate); Module 1 course templates; trials, listings and Explore; academy roles beyond owner and coach; in-app chat; native apps; SMS or WhatsApp sign-in codes; payment gateway; memory book; monthly reports.

## 4. Success measures

| Type | Measure | Target |
|---|---|---|
| North-star | Share of class sessions with a parent update sent within 1 hour of class end | 80% |
| Effort | Median coach time from class end to published update | Under 2 min |
| Habit | Class days with a post, per coach | 4 of 5 |
| Reach | Families opening updates each week | 60%+ |
| Guardrail | Privacy or data incidents | 0 |
| Guardrail | Crash-free sessions | 99%+ |
| Guardrail | Messages sent in quiet hours (8:30 pm to 9 am) | 0 |

Analytics events (names only, no children's data): `signed_in`, `academy_created`, `batch_created`, `invite_sent`, `invite_accepted`, `attendance_saved`, `signal_sent`, `update_drafted`, `update_published`, `item_opened`, `reminder_sent`, `ai_draft_accepted`, `ai_draft_edited`.

## 5. Release criteria

Pilot v1 launches only when the Stage 7 gate passes (`docs/11_launch_readiness_checklist.md`).

## 6. Assumptions to watch (product only)

- Coaches will accept reviewing AI drafts instead of writing.
- Parents will install the app (PWA) so push notifications work, especially on iPhone.
- Hinglish voice-to-text is good enough for 8 of 10 notes.
