# CloudResearch Connect: everything needed to launch

Field-by-field copy plus the settings that break the study if they are wrong.
Verified against Connect's own documentation, not from memory:
[Setting Up a Project](https://connect-researcher-help.cloudresearch.com/hc/en-us/articles/4416207746068-Setting-Up-a-Project),
[Integrating your Survey](https://connect-researcher-help.cloudresearch.com/hc/en-us/articles/21181529476500-How-to-Integrate-your-Survey-with-Connect),
[Project Completion](https://connect-researcher-help.cloudresearch.com/hc/en-us/articles/5046202939796-Project-Completion),
[Project Link](https://connect-researcher-help.cloudresearch.com/hc/en-us/articles/4416245469332-Project-Link).

---

## 1. The one thing that would block every rater

Connect appends its participant identifier to your Project URL as **`participantId`**.
The form reads exactly that (`index.html`, `const PID = url.get("participantId")`), and
**the Start button is disabled without it**, deliberately, because a rater with no ID
cannot be matched to a Connect submission or paid.

So the Project URL must be the bare page, with no query string of its own:

```
https://user-dramm.github.io/cloudresearch-pilot/
```

Connect then sends people to `...?participantId=XXXX`. If you ever add your own
parameter to the Project URL, check the result is `?a=b&participantId=...` and not two
`?` characters. That is the failure mode, and it silently disables Start for everyone.

**Test it before launching** by opening the exact link Connect generates. Not a link
you typed by hand.

The form also captures `assignmentId` and `projectId` if present. Both optional per the
docs, but `assignmentId` is unique per participant per session, which makes matching a
Sheet row to a Connect submission unambiguous if someone disputes a rejection.

## 2. Completion: belt and braces

Connect needs either an end-of-study redirect or a completion code. This study uses
**both**, because either one alone has a failure mode.

- **Completion code:** `EMBR7K2QX4`. Set it as a *fixed* code in Connect and it must
  match `completionCode` in `config.js` exactly. Connect disallows `0`, `1`, `I` and
  `O` in fixed codes; this one is clean.
- **Redirect URL:** copy it from the end of the Create-a-Study wizard and paste it into
  `redirectUrl` in `config.js`. The form then sends people back automatically four
  seconds after their answers are saved, and still shows the code in case the redirect
  fails.

A fixed code is shareable by definition, so **approve against the Sheet, not the code**.
A real submission is a row carrying that participant's ID that clears the gates.

## 3. Study fields

**Project name, the one participants see.** It sits in a LIST of studies next to others,
so it wants to be a short label rather than a sentence. An earlier version of this file
put a full sentence here, which reads wrong in a list.

> Training Video Feedback

Alternatives, same neutrality: "Training Video Feedback (25 min)", which helps people opt
out early but may duplicate the duration Connect already shows, or "Short Training Videos:
Your Opinion".

Whatever you pick, keep these words OUT of it: versions, old, new, updated, original, AI,
compare. A rater who works out that the two videos are two builds of one course stops
judging them and starts guessing which is which.

**Internal name**, your dashboard only, so it can say exactly what this is:

> Training video quality comparison, pilot, Aug 2026

**Description**

> We make short training videos for people who work in senior care, and we want honest
> feedback on how they come across. You'll watch two videos, about nine minutes each,
> and answer four quick questions about each one. At the end you'll say which of the two
> you thought was better and why.
>
> You don't need any healthcare experience. We want an ordinary viewer's reaction, not
> an expert review. There are no right answers and we are not testing you.
>
> Please plan for about 25 minutes in one sitting, on a desktop or laptop with sound.
> Each video plays in two parts with a short pause between them. The questions stay
> locked until a video has actually played, and skipping ahead rewinds you, so there is
> no way to rush it.

**Estimated time:** 25 minutes
**Payment:** $4.17 (that is $10.01/hour for 25 minutes)

Say "about nine minutes each" and "about 25 minutes" honestly. Understating length is
the most reliable way to earn poor ratings on a panel where participants talk to each
other.

## 4. Settings that matter

| Setting | Value | Why |
|---|---|---|
| **Project URL** | the bare Pages URL, no query string | Connect appends `?participantId=` |
| **Completion** | fixed code `EMBR7K2QX4` | must match `config.js` |
| **Redirect** | paste the wizard's URL into `config.js` | the more reliable of the two methods |
| **Devices** | desktop and laptop **only** | this is the PRIMARY control, not a backup. The form blocks anything under 820px, which covers every phone and portrait tablets, but a landscape iPad at 1024px+ would still load it. Do not leave phone or tablet ticked |
| **Exclude previous participants** | ticked on every run after the first | stops the dry-run three, and stops anyone taking two pairs |

## 5. Screening

Keep it minimal. Every screener slows the fill, and this study wants an ordinary viewer.

- Location: United States
- Language: fluent English
- Age: 18+
- **No occupation or industry screener.** You are not recruiting care workers. A care
  worker's professional opinion of the *content* is a different question from the one
  being asked, and screening for it would shrink the pool for no gain.

## 6. Instructions on the Connect task page

> Open the study link and keep the tab open until you see the completion screen.
>
> You'll need sound, on a desktop or laptop. Each video plays in two parts with a short
> black pause in the middle. Keep watching, it hasn't ended.
>
> A code word appears on screen during the second part of each video. There's a box
> right under the video: type it in as soon as you see it.
>
> Your progress is saved as you go. If your browser closes or you lose power, reopen
> this same link on the same computer and you'll carry on from where you stopped.
>
> At the end you'll be sent back here automatically. If that doesn't happen, paste the
> code shown on screen.

## 7. How many to order

The endpoint hands each arriving rater whichever pair has the fewest people, so the
cells fill evenly without you managing anything. But at exactly 35 completions across
five pairs there is no slack, and the balancer only lands 7-everywhere about half the
time. Two options:

- **One study, ~35 ordered, then top up.** Export the Sheet, check the per-pair counts
  that `analysis.py` prints under Clause 1, and order the difference. Top-ups go
  automatically to the thinnest pair. Median cost 35 completions, 90% of runs done by 38.
- **Five studies of 7, one per pair**, each with `?pair=P1` … `?pair=P5` on the URL.
  Guarantees exactly 7 per cell for exactly 35 completions. More setup, and
  *exclude previous participants* must be ticked on studies 2 through 5. A pinned pair
  still asks the endpoint for its alternation index, so A/B order keeps taking turns.

`tools/assign_sim.py` and `tools/power.py` have the numbers behind both.

## 7b. CLEAR THE ASSIGNMENTS TAB FIRST. This one is easy to miss and expensive.

The endpoint balances by handing each arriving rater whichever pair currently has the
fewest, and it counts rows in the `assignments` tab. Testing leaves rows there. Measured
on 2026-08-07, after a day of testing:

```
{"P1":2,"P2":6,"P3":2,"P4":1,"P5":1}
```

Twelve phantom raters, six of them on P2. Launch against that and the balancer believes P2
is already two-thirds full and steers real raters away from it, so P2 finishes short. Clause
1 needs new ahead in at least 4 of the 5 pairs, which needs every pair to have enough raters
for "ahead" to mean anything, so an under-filled cell is not cosmetic.

**Before launching: delete every row in the `assignments` tab except the header.** Then
confirm with one call that the counts are back to zero:

```
curl -sL "<endpoint>?action=assign&token=embr-pilot-2026-07&pid=PRELAUNCH&pairs=P1,P2,P3,P4,P5"
```

That prints a `counts` object. Every pair should read 0 or 1. Delete the `PRELAUNCH` row
afterwards too. Note `curl` needs **-L**: Apps Script 302-redirects to
`script.googleusercontent.com`, and without it every call looks like a failure.

## 8. Two runs

**Dry run first:** a separate study, 3 participants, ~$18 with fees. Its job is to test
the cost model and the instrument against reality before the main spend. Afterwards
check the Sheet for three rows with sensible watch percentages, correct code words,
sessions around 25 minutes, and (the thing to actually watch) whether anyone wrote
anything in the optional boxes. If the written feedback is thin, that is the moment to
make the "why" question required for the raters who see it.

**Then the main run.** Connect pays completions only, so expect to launch more than
your target to land it.

## 9. Approving and rejecting

`python3 tools/decode_responses.py responses.csv --only-problems` prints the reject
shortlist with a reason per row. Work from that.

**Reject only on the objective gates:** didn't watch enough, wrong code word, impossible
playback speed, session impossibly short.

**Never reject on someone's rating.** A rater who preferred the archived version is the
finding. It is the entire reason to run a blind study. Rejecting it is dishonest and
self-defeating: unfair rejections follow you, and Connect participants talk, so your
next study fills slower.
