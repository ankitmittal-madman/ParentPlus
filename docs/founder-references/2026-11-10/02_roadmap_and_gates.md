# 02. Roadmap and gates

**In short:** From approved specs to real families using Parent Plus, in small steps you can see, try and approve. About 10 to 12 weeks to the first real families, if each gate passes first time. Each stage ends at a gate: a checklist the founder ticks personally. Nothing moves on until every box is ticked.

The interactive version is `Parent_Plus_Build_Journey.html`; both are generated from the same plan.

| Stage | Name | Length | Who leads |
|---|---|---|---|
| 0 | Get ready | 1 week | Founder |
| 1 | Foundation | 1 to 2 weeks | AI co-founder, founder approves |
| 2 | Class setup | 1 week | AI co-founder, founder approves |
| 3 | Attendance loop | 1 week | AI co-founder, founder approves |
| 4 | Class updates and moments | 2 weeks | AI co-founder, founder approves |
| 5 | AI assist | 2 weeks | AI co-founder, founder approves |
| 6 | Reminders and changes | 1 to 2 weeks | AI co-founder, founder approves |
| 7 | Pilot launch readiness | 1 week | AI co-founder, founder approves |
| 8 | Pilot with real families | 4 weeks | AI co-founder, founder approves |
| 9 | Fees, done gently | 2 weeks | AI co-founder, founder approves |

## Stage 0: Get ready (1 week)

Before any code, we set up the accounts the product will live in, make nine decisions, and gather real pilot material. This stage is yours; I guide every click.

**Why now:** Code built on the wrong accounts or the wrong decisions has to be redone. One careful week here saves a month later.

**What we build**

- No code yet. You create the startup's accounts, all on free plans, owned by the startup and not by any one person's work account.
- You make the nine decisions on the Decisions board.
- You collect pilot material: real batches, families (with their permission), 10 real coach updates and 10 short voice notes.

**What you'll see:** A 'control room' you own: GitHub for the code, Supabase for the data, Vercel for hosting, PostHog for usage, all with two-step login switched on.

**Your part**

- Work through the 14 steps in 'Your first week' below.
- Make the nine decisions.
- Book a weekly 45-minute demo slot.

**Gate: all must be true before moving on**

- [ ] All accounts are created under the startup's own Google account (not a work account), with two-step verification on
- [ ] Every password and key is saved in a password manager, never in chat, email or WhatsApp
- [ ] All nine decisions (D1 to D9) are made
- [ ] The pilot academy and coach have agreed to try it
- [ ] Batch details and the family list are collected, with the families' permission
- [ ] 10 real coach updates and 10 short Hinglish voice notes are collected as test material
- [ ] A weekly 45-minute demo slot is in the calendar

Decisions at this stage: D1, D2, D3, D5, D6, D7, D8, D9

**Cost:** ₹0, plus about ₹800 to ₹1,200 a year for a domain (recommended). Plus about $20 a month for the AI builder if you choose D1 option A.

## Stage 1: Foundation (1 to 2 weeks)

The empty shell of the app, built properly. You can open a link on your phone, install it like an app, and sign in as a coach or a parent. Nothing useful yet, but everything underneath is real: security, backups, automatic checks and error tracking.

**Why now:** Strong foundations are what make every later stage fast and safe. Product teams at Google call this a 'walking skeleton': thin, but connected end to end.

**What we build**

- The code repository with automatic checks on every change
- Two environments: 'staging' for trying things, 'production' for real families
- Sign-in (per decision D2), automatic profiles, and 'create your academy' for coaches
- The core database (19 tables) with access rules on every table and 55 security tests
- An installable app (PWA) with English and Hindi switching
- Nightly encrypted backups, error tracking and usage analytics (with no children's data)

Module 2 features: M2-45, M2-46, M2-58

**What you'll see:** A staging link you can install on your phone. Sign in, create 'FitKids Gym', switch to Hindi. Every change I make also gets its own preview link, so you can try it before it goes live.

**Your part**

- Follow the demo script on an Android phone and an iPhone
- Read the build diary (10 minutes a day)
- Approve the gate in the Friday demo

**Gate: all must be true before moving on**

- [ ] You installed the app on an Android phone and an iPhone, and signed in as a coach and as a parent
- [ ] Every change shows a green 'all checks passed' tick before you are asked to look at it
- [ ] Every change comes with its own preview link that you can try
- [ ] All database security tests pass (55 today; more are added every stage)
- [ ] Last night's backup exists, and one restore drill into staging worked
- [ ] A test error appears in PostHog within a minute, and no child's name appears anywhere in analytics
- [ ] The first screen loads in under 3 seconds on a mid-range Android phone on 4G

Decisions at this stage: D4

**Cost:** ₹0

## Stage 2: Class setup (1 week)

Coaches set up each batch once and the calendar fills itself. They add children and send each family an invite link on WhatsApp; the parent opens it and sees their child's class.

**Why now:** Everything else (attendance, updates, reminders, fees) hangs off 'this class on this date'. Getting it right, and easy, comes first.

**What we build**

- Batches with repeating schedules, rooms and fees (M2-01)
- Sessions created automatically 4 weeks ahead, skipping holidays
- Add a child, invite the family by link, add a second guardian (M2-02)
- A simple student list (M2-49)
- Edit or cancel a single session

Module 2 features: M2-01, M2-02, M2-49

**What you'll see:** Your pilot coach's real batches, set up in minutes. A parent joins from a WhatsApp invite and sees Gym class on Mon, Wed and Fri.

**Your part**

- Sit with the pilot coach while they set up their batches (don't help!)
- Join as a parent from an invite on your own phone

**Gate: all must be true before moving on**

- [ ] The pilot coach set up all their real batches without help, in under 10 minutes (you watched)
- [ ] Sessions appear for the next 4 weeks at the right India times
- [ ] An invite link sent on WhatsApp lets a parent join in under 1 minute
- [ ] A second guardian (for example a grandparent) can join from their own invite
- [ ] With two phones side by side, each parent sees only their own child

**Cost:** ₹0

## Stage 3: Attendance loop (1 week)

The first real loop. A parent sends 'missing today'; the coach confirms attendance in one action; the parent sees it straight away.

**Why now:** This is the smallest loop that gives both sides real value, and the first habit we want coaches to form.

**What we build**

- Parent quick signals: running late, missing today, dropped off (M2-06)
- Fast attendance with smart defaults (M2-09)
- Attendance reaches parents as a typed item; parent week view
- A first 'Today' list for coaches (M2-41, basic)

Module 2 features: M2-06, M2-09, M2-41

**What you'll see:** The coach confirms 12 children in a few seconds; the parent's phone shows 'Rudraansh attended Wednesday's class'.

**Your part**

- Ask the pilot coach to use it for three real classes
- Check from a parent phone

**Gate: all must be true before moving on**

- [ ] Marking attendance for a class of 12 takes under 10 seconds
- [ ] The parent sees attendance within 5 seconds of the coach saving it
- [ ] A 'missing today' signal marks the child absent in advance
- [ ] It still works on a slow connection (tested at 3G speed)
- [ ] The pilot coach used it for three real classes in a row

**Cost:** ₹0

## Stage 4: Class updates and moments (2 weeks)

The heart of Parent Plus. After class the coach posts what happened, adds photos, a 'try at home' idea or a milestone moment, previews exactly what parents will see, and sends. Photos reach only families who agreed.

**Why now:** This is the value parents feel every day, and where trust is won or lost, so consent is built in from the first photo.

**What we build**

- Class updates and personal notes, with a parent preview (M2-13, M2-16, M2-20)
- Consent choices for each family (M2-25)
- Quick photo, video and audio capture; tagging; safe sharing (M2-26, M2-27)
- Try-at-home activities and milestone moments (M2-47, M2-48)
- Class announcements (M2-50)
- The parent feed showing each item type, with the simple fallback (M2-58)

Module 2 features: M2-13, M2-16, M2-20, M2-25, M2-26, M2-27, M2-47, M2-48, M2-50, M2-58

**What you'll see:** The coach posts an update with 3 photos in under a minute. One parent sees it with photos; another parent, who said no to group photos, never receives the group picture.

**Your part**

- Run the two-phone consent test yourself
- Score 5 real updates: would you be proud to send this?

**Gate: all must be true before moving on**

- [ ] Posting an update with photos takes under 1 minute
- [ ] The two-phone consent test passes: a family that said no never receives the group photo
- [ ] Every item type looks right in the parent app, and an unknown type shows the simple fallback
- [ ] Photos are under 300 KB each and open in under 2 seconds
- [ ] A parent can share an update with family without exposing other children

**Cost:** ₹0 (photos fit inside the 1 GB free storage for the pilot)

## Stage 5: AI assist (2 weeks)

Now we make it effortless. The coach speaks for 10 seconds in Hinglish, and the app writes the update and personal notes for them to approve. Children's names are removed before anything is sent to the AI.

**Why now:** Daily posting only becomes realistic when it takes under 2 minutes. This is the promise that makes Parent Plus different.

**What we build**

- Voice to update (M2-14)
- The prefill-and-approve AI engine behind a swappable adapter (M2-37)
- Name removal before every AI call (M2-38)
- AI polish and tone checks (M2-16)
- Spotlight rotation, quick observations and AI personal notes (M2-18, M2-19, M2-20)

Module 2 features: M2-14, M2-37, M2-38, M2-16, M2-18, M2-19, M2-20

**What you'll see:** Your own 10 test voice notes turned into drafts you'd be happy to send.

**Your part**

- Score the 10 AI drafts from 1 to 5
- Try it in a real class with the pilot coach

**Gate: all must be true before moving on**

- [ ] On your 10 test voice notes, at least 8 drafts are good enough to send with small or no edits (you score them)
- [ ] The logs prove no child's name or phone number was sent to the AI
- [ ] From class end to published update takes the coach under 2 minutes (median)
- [ ] AI use stays inside the free tier, with a spending cap in place
- [ ] The coach can always switch AI off and write by hand

Decisions at this stage: D5

**Cost:** ₹0 on the free AI tier (see D5 about data terms)

## Stage 6: Reminders and changes (1 to 2 weeks)

Parents get the right message at the right time: the get-ready reminder the evening before, instant notice when a class is cancelled or moved, and announcements. Never at night.

**Why now:** Reminders are what bring parents back between classes, and what save the coach from twenty 'is class on today?' messages.

**What we build**

- One outbox for every message: web push, with ready-to-send WhatsApp messages as the fallback (M2-40)
- The evening-before get-ready reminder (M2-04)
- Cancel, restore, move, extra class and holiday, with parent RSVP (M2-05)
- Quiet hours and message caps
- The full 'Needs you' list (M2-41)

Module 2 features: M2-40, M2-04, M2-05, M2-41

**What you'll see:** Cancel Friday's class: only that batch's families get a polite message within a minute, and their week view updates.

**Your part**

- Install the app on an iPhone and allow notifications
- Try a cancellation and an extra class

**Gate: all must be true before moving on**

- [ ] The evening-before reminder arrives on Android, and on an iPhone with the app installed
- [ ] Nothing is sent between 8:30 pm and 9 am
- [ ] A cancellation reaches only the affected families, within 1 minute
- [ ] Families without notifications get a ready-to-send WhatsApp message instead
- [ ] Parents can answer yes or no to an extra class, and the coach sees the count

**Cost:** ₹0

## Stage 7: Pilot launch readiness (1 week)

We stop adding features and get ready for real families: privacy wording, consent screens, a support channel, coach training, and a full rehearsal of a class day.

**Why now:** First impressions with real parents are hard to repeat. Every top product team runs a launch review before going live.

**What we build**

- Privacy policy, consent wording and a 'delete my data' request flow
- End-to-end tests for every key journey on the live environment
- The north-star dashboard (update within 1 hour; coach time under 2 minutes)
- Production environment, hosting decision carried out, rollback plan
- A known-issues list and a support WhatsApp number

**What you'll see:** A full rehearsal: you play the coach and a friend plays the parent, through a whole class day.

**Your part**

- Get the privacy wording reviewed (ideally by a lawyer)
- Train the pilot coach (20 minutes)
- Sign off the launch

**Gate: all must be true before moving on**

- [ ] Privacy policy and consent wording are reviewed and live in the app
- [ ] Every key journey passes automated end-to-end tests on the live environment
- [ ] A restore drill worked on production backups
- [ ] The north-star dashboard is live
- [ ] The pilot coach was trained in under 20 minutes and can run a class day alone
- [ ] Hosting is on a plan that allows commercial use (per D4)
- [ ] You can honestly say: 'I'd be proud to show this to a parent'

Decisions at this stage: D4

**Cost:** ₹0 to about $20 a month, depending on D4

## Stage 8: Pilot with real families (4 weeks)

One academy, 20 to 30 families, four weeks. We watch the numbers, fix the top issues every week, and decide what comes next from real use.

**Why now:** Real use beats opinions. The pilot tells us whether the daily habit forms before we add fees.

**What we build**

- Weekly fixes for the top reported issues
- Small improvements only; no big new features
- A weekly pilot report in plain words

**What you'll see:** A weekly pilot report: posting rate, parent opens, coach time, issues fixed.

**Your part**

- Talk to the coach weekly
- Collect issues from parents in the support chat
- Decide the next priorities with me

**Gate: all must be true before moving on**

- [ ] Coaches post on at least 4 of every 5 class days, two weeks running (your pilot rule)
- [ ] At least 60% of families open updates each week
- [ ] No privacy or data incidents
- [ ] The top 5 reported issues are fixed
- [ ] The coach says they'd be upset if the app went away

**Cost:** ₹0 within free limits (we watch storage, emails and the Supabase pause rule)

## Stage 9: Fees, done gently (2 weeks)

Only once the daily habit is proven: fee plans, a clear tracker, pay-by-UPI links, the gentle reminder ladder and automatic receipts.

**Why now:** Asking for money works best once parents already see value every day. That's your pilot rule, and it's right.

**What we build**

- Fee plans and automatic dues (M2-31)
- Fee tracker (M2-32)
- Pay by UPI link or QR, with money going straight to the coach (M2-33)
- The gentle reminder ladder (M2-34)
- Automatic receipts (M2-35)

Module 2 features: M2-31, M2-32, M2-33, M2-34, M2-35

**What you'll see:** On the 1st, every family gets a value-first fee note and can pay by UPI in under 30 seconds.

**Your part**

- Test UPI payment on GPay, PhonePe and Paytm with small amounts
- Approve the reminder wording

**Gate: all must be true before moving on**

- [ ] Dues are created automatically for every family on the 1st
- [ ] A parent can pay by UPI in under 30 seconds on GPay, PhonePe and Paytm (tested)
- [ ] Reminders follow the gentle ladder: at most 3 automatic messages, never at night
- [ ] Receipts arrive automatically once the coach confirms
- [ ] In the first cycle, 85% of fees are paid within 5 days of the due date

**Cost:** ₹0 (UPI goes straight to the coach; no gateway fees)

## After the pilot

- **Course design (Module 1)**: Templates, skills and milestones that pre-fill updates and observations
- **Progress timeline and monthly reports**: M2-21, M2-23
- **Memory book and 'then and now'**: M2-28, M2-29
- **Academy accounts and roles**: M2-44
- **Trials, listings and Explore**: M2-53, M2-54, M2-55
- **Coach insights and plan billing**: M2-56, M2-57
- **Safe pick-up and auto-attendance**: M2-10, M2-11
- **In-app chat and calendar sync**: M2-51, M2-52
