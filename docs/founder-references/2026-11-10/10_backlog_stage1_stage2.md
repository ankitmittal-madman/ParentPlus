# 10. Backlog: Stage 1 (Foundation) and Stage 2 (Class setup)

**In short:** the first 16 stories, in build order. Each one is small, has acceptance criteria you can check on a phone, and ends with a preview link.

## Stage 1: Foundation

**S1-01 Repository and automatic checks**
As the founder, I want every change checked automatically, so that broken code never reaches me.
- Given a pull request, when it opens, then lint, types, unit tests, database tests and build run, and a green or red result shows on it.
- Given any red check, when someone tries to merge, then merging is blocked.

**S1-02 Preview links**
As the founder, I want a private link for every change, so that I can try it before it goes live.
- Given a pull request, when checks pass, then a preview URL is posted on it within 5 minutes.

**S1-03 Staging and production**
As the founder, I want practice and real environments kept apart, so that experiments never touch families' data.
- Given the two Supabase projects, when migration 0001 runs, then it is applied to staging by CI, and to production only by a manual gate release.

**S1-04 Sign in**
As a coach or parent, I can sign in with Google or with an email code, so that I don't need a password.
- Given a new person, when they sign in for the first time, then a profile is created automatically (test T01).
- Given the email option, when they enter their email, then a 6-digit code arrives within 1 minute (sent through Resend).

**S1-05 Choose your path**
As a new user, I can say "I run classes" or "My child attends classes", so that I land in the right place.
- Given "I run classes", when I enter an academy name and city, then the academy is created and I'm its owner (test T04).
- Given "My child attends classes", then I see "Your coach will send you an invite link" and how to get one.

**S1-06 Installable app**
As any user, I can add Parent Plus to my home screen, so that it opens like an app.
- Given Android Chrome or iPhone Safari, when I follow the install hint, then the app opens full-screen with the Parent Plus icon.

**S1-07 English and Hindi**
As any user, I can switch the language, so that I use the app comfortably.
- Given the language setting, when I switch to Hindi, then every screen in Stage 1 shows Hindi text, and my choice is remembered (test T55).

**S1-08 Usage and error tracking, privacy-safe**
As the founder, I want to know when something breaks, without exposing families' data.
- Given a test error, when it happens, then it appears in PostHog within 1 minute.
- Given any event, then it contains no child's name, photo or free text.

**S1-09 Nightly encrypted backup**
As the founder, I want a copy of the data every night, so that nothing is ever lost.
- Given the nightly schedule, when it runs, then an encrypted backup file is stored for 14 days.
- Given a backup, when a restore drill runs into staging, then the data matches.

## Stage 2: Class setup

**S2-01 Create a batch**
As a coach, I can create a batch with its days, times, venue, room, age group and monthly fee, so that my week is set up once.
- Given "Mon, Wed, Fri, 5:30 to 6:30 pm", when I save, then sessions appear for the next 4 weeks at India time (tests T05 to T07).

**S2-02 Keep the calendar filled**
As a coach, I want sessions to keep appearing automatically, so that I never re-enter them.
- Given an active batch, when the nightly job runs, then sessions exist for the next 4 weeks, with no duplicates (test T06).

**S2-03 Change one session**
As a coach, I can cancel, restore or move a single session, so that the plan matches reality.
- Given a session, when I cancel it, then its status is cancelled and the recurring rule is unchanged.

**S2-04 Add a child and invite the family**
As a coach, I can add a child and share an invite link on WhatsApp, so that the parent joins without a sign-up form.
- Given a new child, when I tap share, then WhatsApp opens with a ready message and the link.
- Given the link, when the parent opens it and signs in, then they become the child's guardian and see the class (tests T32, T33).
- Given a used or fake link, then it is refused politely (tests T35, T36).

**S2-05 Second guardian**
As a parent, I can invite my partner or a grandparent, so that they get updates too.
- Given my child, when I share a family invite, then the new guardian sees the child but isn't made the fee payer (test T34).

**S2-06 Student list**
As a coach, I see my children by batch, with their guardians and status, so that I know who's in.
- Given two batches, when I filter by one, then only its children show; other academies' children never do (test T28).

**S2-07 Pause or leave**
As a coach, I can mark a child paused or left, with a reason, so that the roster stays accurate.
- Given a paused child, then they don't appear on that batch's attendance list.

**Gate check for Stage 2:** see `02_roadmap_and_gates.md`.
