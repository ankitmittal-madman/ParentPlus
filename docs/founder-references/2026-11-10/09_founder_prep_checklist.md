# 09. Founder prep checklist (Stage 0)

**In short:** about 4 to 5 hours over one week. Fourteen steps, each with why it matters and exactly what to do. Never paste passwords or keys into chat: they go only in the password manager.

## Step 1. Create the startup's own Google account (15 min)

*Why:* Everything the company owns hangs off this account. If it's a personal or work account, ownership gets messy later.

- [ ] Create a new Gmail account just for the startup (for example team.parentplus@gmail.com)
- [ ] Turn on 2-step verification (Google Account, then Security)
- [ ] Don't use your work email or work laptop for the startup: check your employment terms about side projects, because work systems can create ownership questions

Link: https://accounts.google.com/signup

## Step 2. Set up a password manager (10 min)

*Why:* We'll create about a dozen passwords and secret keys. They must never travel by chat, email or WhatsApp.

- [ ] Install Bitwarden (free) on your phone and laptop
- [ ] Create a vault called 'Parent Plus'
- [ ] Share it with your co-founder (Bitwarden's free organisation supports 2 people)

Link: https://bitwarden.com

## Step 3. Buy a domain (if D3 = yes) (15 min)

*Why:* Sign-in emails to parents need a real domain, and links like parentplus.in look trustworthy.

- [ ] Search for a short name (for example parentplus.in or getparentplus.com)
- [ ] Buy it for 1 year with the startup Google account (about ₹800 to ₹1,200)
- [ ] Don't add hosting or email extras; we don't need them

Link: https://www.cloudflare.com/products/registrar/

## Step 4. Create GitHub (where the code lives) (10 min)

*Why:* GitHub stores every line of code and its full history, runs our automatic checks, and keeps our nightly backups.

- [ ] Sign up with the startup email; turn on two-factor authentication
- [ ] Create a free organisation called 'parentplus'
- [ ] Inside it, create a private repository called 'parentplus-app' (tick 'Add a README')

Link: https://github.com/signup

## Step 5. Create Supabase (database, sign-in, files) (15 min)

*Why:* Supabase holds all the data with access rules on every table, and handles sign-in, photos and live updates.

- [ ] Sign up using 'Continue with GitHub'
- [ ] Create two free projects: 'parentplus-staging' and 'parentplus-prod'
- [ ] Choose region 'South Asia (Mumbai)' for both
- [ ] Save each database password in Bitwarden. Never paste keys into chat

Link: https://supabase.com/dashboard

## Step 6. Create Vercel (hosting) (5 min)

*Why:* Vercel turns each code change into a preview link you can try, and hosts the live app.

- [ ] Sign up with 'Continue with GitHub' on the free Hobby plan
- [ ] Don't import anything yet; I'll do that with you in Stage 1

Link: https://vercel.com/signup

## Step 7. Get a Google AI Studio key (AI drafts) (5 min)

*Why:* This powers voice-to-update and drafting in Stage 5, on the free tier.

- [ ] Sign in with the startup Google account
- [ ] Click 'Get API key', create one, and save it in Bitwarden
- [ ] Don't use it anywhere yet

Link: https://aistudio.google.com

## Step 8. Create PostHog (usage, errors, feature switches) (5 min)

*Why:* One free tool tells us how the app is used, catches errors, and lets us switch features on for a few users first.

- [ ] Sign up for the free plan (no card needed)
- [ ] Create a project called 'Parent Plus'

Link: https://posthog.com

## Step 9. Create Resend (sign-in emails, if D3 = yes) (10 min)

*Why:* Supabase's built-in email only sends to your own team, so parents need this to receive sign-in codes. Free: 3,000 emails a month, 100 a day.

- [ ] Sign up for the free plan
- [ ] Add your domain; I'll guide you through the DNS records in Stage 1

Link: https://resend.com

## Step 10. Set up the AI builder (if D1 = A) (15 min)

*Why:* The AI coding agent writes, tests and proposes each change inside your GitHub, so you never need to install developer tools.

- [ ] Subscribe to Claude Pro with the startup email (about $20 a month), or choose the free Gemini CLI
- [ ] That's all for now; in Stage 1 we open a free GitHub Codespace (a browser-based workspace) together and start the agent there

Link: https://claude.ai

## Step 11. Make the nine decisions (30 min)

*Why:* Each one changes what gets built first, or what it costs.

- [ ] Go to the Decisions board below
- [ ] Read the recommendation, then pick an option
- [ ] Note any questions for our Friday call

## Step 12. Prepare the pilot material (2 to 3 hours over the week)

*Why:* Real data and real examples are how we test properly, and how we know the AI drafts are good enough.

- [ ] Get the pilot academy's OK to try Parent Plus
- [ ] List each batch: name, days, times, venue, room, monthly fee
- [ ] List children (first names) with one parent contact each, with the parents' permission
- [ ] Collect 10 real updates the coach has sent on WhatsApp
- [ ] Record 10 voice notes of 10 to 20 seconds each, describing a class in Hinglish
- [ ] Optional: a logo; we'll use the prototype's colours

## Step 13. Line up test phones (5 min)

*Why:* Android and iPhone behave differently, especially for notifications.

- [ ] One Android phone and one iPhone you can borrow for 30 minutes at each stage

## Step 14. Book the rhythm (5 min)

*Why:* Small, regular check-ins keep the build on track and you in control.

- [ ] Book a weekly 45-minute demo slot (Fridays work well)
- [ ] Block 10 minutes a day to read the build diary and try preview links

## The nine decisions

### D1. How does the code get written?

*Why it matters:* Speed and reliability of every stage.

- **A.** An AI coding agent works inside your GitHub (Claude Code in a free GitHub Codespace). It writes, tests and proposes every change for your review. *(About $20 a month (Claude Pro). Gemini CLI is a free alternative.)*  **Recommended**
- **B.** I write the code here in chat, and you upload each package to GitHub through the website. *(₹0, but slower, with more copy-paste and more room for mistakes.)*

### D2. How do people sign in during the pilot?

*Why it matters:* The first thing every parent sees; it also affects cost and paperwork.

- **A.** Google sign-in, plus a one-time code by email. *(Free. Needs a domain for the emails (D3).)*  **Recommended**
- **B.** Phone number with an SMS code. *(Familiar to Indian parents, but needs DLT registration as a business and costs money per SMS.)*
- **C.** Google sign-in only. *(Simplest and free, but leaves out parents without a Google account.)*

### D3. Do we buy a domain now?

*Why it matters:* Needed for sign-in emails, and makes links look trustworthy.

- **A.** Yes, for example parentplus.in. *(About ₹800 to ₹1,200 a year.)*  **Recommended**
- **B.** Not yet. *(₹0. Then sign-in must be Google only (D2 = C).)*

### D4. Where do we host once real families use it (Stage 7)?

*Why it matters:* Vercel's free Hobby plan is for non-commercial use only, which is fine while we build but not for a business.

- **A.** Move to Vercel Pro: the same setup we build on, with no conversion work. *(About $20 a month.)*
- **B.** Move to Cloudflare's free plan, which allows commercial use. Needs a small conversion step and re-testing. *(₹0.)*
- **C.** Decide at Stage 7: try Cloudflare first, and if the conversion isn't clean within a day, pay for Vercel Pro. *(₹0 or about $20 a month.)*  **Recommended**

### D5. Which AI writes the drafts?

*Why it matters:* Draft quality, cost, and what happens to the text we send.

- **A.** Google Gemini's free tier, with children's names removed before anything is sent. *(₹0. Free tiers may use submitted text to improve their products, which is why names are removed.)*  **Recommended**
- **B.** A paid AI plan whose terms say it won't train on your data. *(Roughly ₹500 to ₹1,500 a month at pilot volume.)*

### D6. Which languages at launch?

*Why it matters:* Every word in the app is translated and tested.

- **A.** English and Hindi. *(Small extra effort per stage.)*  **Recommended**
- **B.** English only. *(Fastest, but excludes many home tutors.)*
- **C.** English, Hindi and Marathi. *(More effort; useful if the pilot is in Maharashtra.)*

### D7. Who approves each gate?

*Why it matters:* Clear ownership keeps decisions fast.

- **A.** One named approver decides; the other founder reviews. *(Fast, with clear accountability.)*  **Recommended**
- **B.** Both founders must approve. *(Slower, but shared.)*

### D8. How big is the pilot?

*Why it matters:* Small enough to support personally, big enough to learn from.

- **A.** 1 academy, 1 to 3 coaches, 20 to 30 families. *(Manageable within free limits.)*  **Recommended**
- **B.** 2 to 3 academies. *(More learning, but more support load and closer to free limits.)*

### D9. Which progress scale do coaches use?

*Why it matters:* Shared by Module 1 and Module 2; hard to change once parents are used to it.

- **A.** Started / Practising / Confident (as in your prototype). *(Already in the design.)*  **Recommended**
- **B.** Getting there / Almost / Got it (Module 1 draft). *(Friendlier for very young children.)*

## Stage 0 gate

- [ ] All accounts are created under the startup's own Google account (not a work account), with two-step verification on
- [ ] Every password and key is saved in a password manager, never in chat, email or WhatsApp
- [ ] All nine decisions (D1 to D9) are made
- [ ] The pilot academy and coach have agreed to try it
- [ ] Batch details and the family list are collected, with the families' permission
- [ ] 10 real coach updates and 10 short Hinglish voice notes are collected as test material
- [ ] A weekly 45-minute demo slot is in the calendar
