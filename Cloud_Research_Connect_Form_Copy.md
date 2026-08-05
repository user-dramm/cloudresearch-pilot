# CloudResearch Connect — study setup, field by field

Copy of every field you have to fill in, plus the four settings that break the study if they
are wrong. Nothing here reveals which video is which; participants must never learn that one
version is older than the other, or they will rate the story rather than the video.

---

## 1. Study basics

**Study name** (internal, participants do not see it)

> Training video quality comparison — pilot, Aug 2026

**Title shown to participants**

> Watch two short training videos and tell us which is better

**Description shown to participants**

> We make short training videos for people who work in senior care, and we want honest
> feedback on how they come across. You will watch two videos, about nine minutes each, and
> answer a few questions about each one. Then you will tell us which of the two you thought
> was better and why.
>
> You do not need any healthcare experience. We want an ordinary viewer's reaction, not an
> expert review. There are no right answers and we are not testing you.
>
> Please plan for about 25 minutes in one sitting, on a desktop or laptop with sound. The
> questions stay locked until each video has actually played, so you cannot skip ahead.

**Estimated time:** 25 minutes
**Payment:** set to your platform's rate for 25 minutes (budget assumed ~$7/session)

Say "about nine minutes each" and "about 25 minutes" honestly. Under-stating the length is the
single most reliable way to earn low ratings and slow future recruitment on a panel where
participants talk to each other.

---

## 2. The four settings that matter

| Setting | Value | Why |
|---|---|---|
| **Project URL** | your GitHub Pages URL | Connect appends `?participantId=…`, which the form reads. If your URL already carries a query string Connect appends with `&` — test the exact link Connect generates before launching |
| **Completion** | *fixed* code `EMBR7K2QX4` | Must match `completionCode` in `config.js`. Connect disallows `0`, `1`, `I` and `O` in fixed codes; this one is clean |
| **Devices** | desktop and laptop **only** | Mobile breaks the watch gate. Do not leave tablet or phone ticked |
| **Exclude previous participants** | ticked, on the main run | So the three dry-run people cannot take it again |

Also copy the **Redirect URL** from the end of the Create-a-Study wizard into `redirectUrl` in
`config.js`. Connect treats the redirect as the more reliable completion method: the
participant is sent back automatically instead of having to carry a code across. The form
still shows the code as a fallback.

---

## 3. Screening

Keep it minimal. Every screener narrows the pool and slows the fill, and this study wants an
ordinary viewer.

- **Location:** United States
- **Language:** fluent English
- **Age:** 18+
- No occupation or industry screener. You are not recruiting care workers — you are asking
  whether the video is any good, and a care worker's professional opinion of the *content* is
  a different question from the one being asked here.

---

## 4. Instructions on the Connect task page

> Open the study link and keep the tab open until you see the completion screen.
>
> You will need sound. Each video must play through before its questions unlock — skipping
> ahead or speeding it up will not unlock them any sooner.
>
> Please answer in your own words. One-word answers and copied text will not be approved.
>
> At the end you will get a code and be sent back here automatically. If the redirect does
> not happen, paste the code shown on screen.

---

## 5. Two runs, not one

**Dry run first:** a separate study, 3 participants, ~$21. Its job is to test the cost model
against reality before the main spend. Check the Sheet afterwards for three rows with
sensible watch percentages, real sentences in the comments, and sessions somewhere around 25
minutes. If sessions come in much longer, the main run costs more than budgeted; if the
comments are thin, tighten the instructions before spending the rest.

**Then the main run:** 7 raters per pair. Connect only pays completions, so expect to launch
slightly more than your target to land it; top up at the end rather than over-ordering.

---

## 6. Approving and rejecting

Approve against **the Sheet**, not the completion code. A fixed code is shareable by
definition; a real submission is a row carrying that participant's ID that clears the quality
gates. `analysis.py` prints the exclusion list with a reason per row, and that list is what
you work from.

**Reject only on the objective gates:** didn't watch enough of a video, wrong code word,
impossible playback speed, copy-pasted or one-word text, session impossibly short.

**Never reject on someone's rating.** If a rater preferred the version you were hoping they
wouldn't, that is the finding — it is the entire reason to run the study. Rejecting it is
both dishonest and self-defeating: unfair rejections follow you, and Connect participants talk
to each other, so your next study fills slower.
