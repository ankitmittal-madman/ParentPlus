# 07. Definition of ready and definition of done

**In short:** a story can start only when it's clear what "finished" looks like, and it counts as finished only when every box below is ticked.

## Ready (before work starts)

- [ ] Written as a user story: "As a [coach or parent], I can [do something], so that [benefit]"
- [ ] Acceptance criteria in Given / When / Then form, testable by the founder on a phone
- [ ] Linked to a feature ID (for example M2-09) and a stage
- [ ] Data needs are clear: new tables or columns, access rules, typed items
- [ ] Analytics events named
- [ ] Any decision it depends on has been made
- [ ] Small enough for one pull request

## Done (before the founder is asked to approve)

- [ ] All acceptance criteria are met on the preview link
- [ ] CI is green: lint, types, unit tests, database tests, build
- [ ] New logic has unit tests; new access rules have SQL tests; gate journeys have end-to-end tests
- [ ] RLS reviewed: tested both "can see" and "cannot see"
- [ ] All text is in English and Hindi; no hard-coded strings
- [ ] Works on Android Chrome and iPhone Safari (installed PWA); accessible labels; one-handed use
- [ ] No children's data in logs or analytics; secrets not in code
- [ ] Analytics events fire
- [ ] Docs updated (data model, item contract, decision log) if anything changed
- [ ] Build diary entry written, with a 3-step "try it" note
- [ ] The founder tried it and approved it (or it's queued for the Friday demo)
