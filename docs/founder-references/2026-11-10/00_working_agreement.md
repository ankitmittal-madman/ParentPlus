# 00. Working agreement

**In short:** you decide and approve; I plan, build, test and explain. We move in small stages, and nothing moves to the next stage until its gate is passed.

## Roles

| | Founder (product owner) | AI co-founder (CPTO and builder) |
|---|---|---|
| Decides | Priorities, scope, money, anything about families' data | How it's built (within the stack), and the order of the work inside a stage |
| Does | Prepares accounts and pilot material, tries every preview, talks to the pilot coach, approves gates | Writes plans, code and tests; runs the checks; writes the build diary; flags risks early |
| Never has to | Read code, run servers, install developer tools | Guess what the founder wants. If unsure, it asks |

Approver for each gate: as chosen in decision D7.

## The weekly rhythm

| When | What | Your time |
|---|---|---|
| Monday | The stage plan: what we build this week, why, and the demo script | 10 min to read |
| Every working session | A build diary entry, plus preview links to try | 10 min a day |
| Any time | A decision request, with a recommendation and a deadline | Reply within 48 hours |
| Friday | A 45-minute demo: you try it live; we walk the gate checklist together | 45 min |

## The review loop (every change)

1. I build a small change, with its tests.
2. Automatic checks run: code style, types, unit tests, database security tests, build. Green, or it doesn't move.
3. You get a preview link and a 3-step "try it" note.
4. You tell me in plain words what you expected and what happened. A screenshot helps; no technical words needed.
5. Approved changes join the main code. The stage gate decides when real families see them.

## Stop rules: I always ask before

- spending any money, or adding a tool with usage limits
- changing what personal data we collect, keep or share
- changing a stage's scope, or skipping a gate criterion
- anything that touches the live database outside the normal checked process

## What every update from me contains

What changed, why, how to try it, what it costs, what could go wrong, and what I need from you, all in plain language.

## How to give good feedback

- "I expected X, but I saw Y" is perfect.
- Say how important it is: must fix before the gate, or nice to have.
- If something feels wrong but you can't say why, say that. It's useful.
