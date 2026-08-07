# Start here

Hand this file to Claude Code along with the project folder. The indented blocks are prompts
you can paste straight in.

**Status as of now:** step 1 is done. The Google Sheet exists, the Apps Script endpoint is
deployed and verified working for anonymous users, and the live URL is already wired into
`config.js`. Everything below step 1 is still to do.

**Videos are being made last, on purpose.** That's the right order - every other piece works
with placeholder video IDs, so when the clips land you launch the same hour instead of starting
a scramble. The one exception is the *audit* in step 2, which happens now.

---

## What you're building

A rater on CloudResearch clicks a link and lands on one web page. It plays video 1 with the
questions greyed out underneath until the video has genuinely played. They answer, watch video
2, answer again, choose which was better and say why, then submit. Answers drop into a Google
Sheet. They get a code to paste back into CloudResearch so you know to pay them.

Three moving parts, all free: **a web page** (GitHub Pages), **ten video clips** (YouTube,
unlisted), **a spreadsheet** (Google Sheets, already done).

**Cost: $0 plus what you fund on CloudResearch (~$266).** No credit card touches anything here.

## The five courses

Each is shown twice - the current recreated version and the archived prior version of the same
title. Same course code for both; which is which is recorded only in `decode_key.json`, which
never leaves your machine.

| Pair | Course | Clip labels | Ready? |
|---|---|---|---|
| P1 | EMBR-CC-00051 | `k3ta` `k9vm` | No - new videos were unrendered Synthesia drafts |
| P2 | EMBR-CC-00158 | `k5qd` `k2wj` | Yes |
| P3 | EMBR-CC-00162 | `k8rn` `k4zf` | Yes |
| P4 | EMBR-CC-00175 | `k6hb` `k1ps` | No - new videos were deleted |
| P5 | EMBR-CC-00254 | `k7cy` `k0lg` | Yes |

From each version you use **module 1 + module 3 only**, joined into one ~10-minute clip. So:
20 module files on disk → 10 clips → 10 unlisted YouTube uploads → 2 videos per rater.

A three-pair first wave can launch as soon as its six clips exist; P1 and P4 join later and
pool to the same 35 votes.

## Can raters skip the video?

No. Three layers, tested adversarially:

1. **Questions stay locked** until the video has genuinely played through 90%. Dragging the
   scrubber forward earns no credit.
2. **Speeding up doesn't help.** Credit is capped at real elapsed time, so 2x costs the same
   real minutes as 1x.
3. **A code word is burned into each video** partway through. You can't know it without
   watching that moment, and a wrong one is an automatic exclusion.

Clicking Continue without watching, stripping the lock off with dev tools, and calling the
submit button directly were all tested and all fail. What no software stops is someone playing
it and looking away - the code word catches much of that, the required written comment most of
the rest.

## How raters get spread evenly across the pairs

Not by chance. If each browser picked at random, across 35 raters you'd get a clean 7-7-7-7-7
about **0.1%** of the time and some pair would land 4 or fewer about **61%** of the time - bad,
because the criterion needs new ahead in at least 4 of 5 pairs.

So the endpoint assigns instead. Each rater gets whichever pair currently has the fewest
people, plus an index that alternates who sees the new version first. Re-simulated 4,000
times with 20% abandonment, **72% of runs land within one rater of even** and the smallest
pair was 4. (An earlier draft of this file said 91%. That number was wrong; see the
correction note in README.md.) Order comes out near 50/50 within each pair - 52.8% measured,
the residual being arithmetic rather than bias.

Refreshing doesn't reroll. Someone who opens the link and wanders off stops holding a slot
after 45 minutes. If the endpoint is unreachable the form assigns locally and records that it
did, so a flaky network costs balance, never a session.

---

# The steps

## 1. Google Sheet and endpoint - **DONE**

Deployed, verified anonymous-accessible, and already in `config.js`.

> Housekeeping: delete the `TEST_ENDPOINT` row from the `assignments` tab. It counts toward one
> pair for 45 minutes otherwise.

## 2. Find the old versions · **YOU + DAMIEN** · do this now

The videos live in Synthesia, not in Talon - Talon holds the course artifacts, not the renders.
So this isn't a Claude Code task, and it's the one item that can change the plan rather than
just the schedule.

**The question: does a downloadable old version exist for each of the five?** A missing new
render can be re-run. A missing *old* version means swapping the course.

The specific risk: if the courses were rebuilt by editing the existing Synthesia projects
rather than duplicating them, the old renders may not exist in Synthesia at all. They'd survive
only as published video on the learning platform, or in an archive folder, or in somebody's
downloads. Worth asking Damien directly rather than assuming.

For each of `00051`, `00158`, `00162`, `00175`, `00254`, you need an answer to: *can I get an
MP4 of the version that was live before the recreation?* Three yeses is a three-pair pilot.
Fewer than three and it's worth reconsidering which courses you picked.

Then download everything into one folder, named so the pair and side are unambiguous:

```
00158_old_mod1.mp4   00158_old_mod3.mp4
00158_new_mod1.mp4   00158_new_mod3.mp4
```

## 2b. Check the sources before cutting · **CLAUDE CODE** · 1 minute

> Run `tools/check_sources.sh` on FOLDER_PATH and tell me what it flags.

This is the check your plan doesn't currently have, and it protects the whole result. If the old
version of a course is 480p and the new one is 1080p, raters will reliably prefer the new one -
and you'll have measured an upgrade in render settings rather than the pipeline. That result
would *pass* the pre-registered criterion and be worthless.

The script reports every file, then flags resolution mismatches and duration gaps between the
old and new sides of each pair. A resolution mismatch isn't automatically fatal, but it has to
be either fixed by sourcing a better copy or stated plainly in the writeup as a confound.

## 3. Repo and hosting · **CLAUDE CODE** · you do nothing

> Create a public GitHub repo for this folder, push it, and enable GitHub Pages from main/root.
> The Apps Script endpoint is already set in `config.js` - don't change it. Then run both
> fake-data tests from the README and show me the output, and give me the live Pages URL.

The tests must print **VALIDATED** on the strong-win run and **NOT VALIDATED** on the null run.
Keep that output - it's what answers "how do we know this wasn't rigged."

Public repo is fine: the decode key is gitignored, and the video IDs reach every rater's
browser anyway. Nothing sensitive is in there.

Then walk the form yourself, before any video exists:

```
https://YOUR-PAGES-URL/?participantId=TEST001&selftest=1&pair=P2
```

The videos won't play yet - the IDs are placeholders. `selftest=1` tags the row so the analysis
drops it automatically.

## 4. Build the CloudResearch study · **YOU** · 20 minutes · can happen before the videos

The URL is stable once Pages is live, so set the study up and fund it now, then flip it on when
clips exist. Field-by-field copy is in `Cloud_Research_Connect_Form_Copy.md`. Four settings:

- **Project URL:** the Pages URL from step 3.
- **Completion:** a *fixed* code matching `completionCode` in `config.js`. CloudResearch bans
  `0`, `1`, `I` and `O` in fixed codes; `EMBR7K2QX4` is clean. Also copy the **Redirect URL**
  from the end of the wizard back into `redirectUrl`.
- **Devices:** desktop and laptop only. Mobile breaks the watch gate.
- **Dry run** as a separate small study, 3 participants (~$21), with *exclude previous
  participants* ticked.

Note the account split: the study lives on the CloudResearch login, the data lands in your
Sheet. Two handoffs - they send you the Redirect URL, you send them the exclusion list at
approval time.

## 5. Cut the clips · **CLAUDE CODE** · once the module files exist

Put all the module files in one folder, then:

> The module files are in FOLDER_PATH - module 1 and module 3 of the old and new version of
> each course. Run `tools/make_clips.sh` to build the 10 clips, pick a distinct code word for
> each, and fill in `decode_key.json` with the label / old-new / code-word mapping. **Randomise
> which position in each pair gets old vs new** - if old is always the first label in
> `config.js`, position alone gives it away. Don't commit the decode key.

Needs ffmpeg (`brew install ffmpeg`, free).

The script encodes every clip through identical settings on purpose. Raters are scoring visual
quality, so if old and new were encoded differently, part of what you'd measure is your encoder.

**The one call everything downstream trusts:** which render is the current recreation and which
is the archived prior version. Mislabel it and the study measures the right thing in the wrong
direction, and reports it confidently.

## 6. Upload to YouTube · **YOU** · 15 minutes, the night before launch

All ten into YouTube Studio **in one session**, every one **Unlisted**, blind titles only -
`A-1`, `A-2`, `B-1` - no course name, date, or version anywhere.

One session is what keeps it blind. Ten clips sharing a timestamp tell a rater nothing; five
from today and five from last year tell them everything.

**The night before, not the morning of.** YouTube renders low resolutions first and HD later. A
clip still processing reads as "the video was blurry," which lands in the same column as real
feedback about your content. Check each offers 720p before pointing CloudResearch at anything.

> Here are the ten YouTube IDs and which pair each belongs to: [paste]. Put them in `config.js`,
> enable the pairs whose clips are ready, and tag the commit.

## 7. Dry run, then launch · **YOU**

Launch the 3-participant dry run. Check the Sheet has three rows with sensible watch
percentages, real sentences in the comments, and sessions around 25 minutes. That's what the
dry run is for - testing the cost model against reality before the $245.

Then launch the main run at 7 raters per pair. CloudResearch only pays completions, so expect to
launch slightly more than 35 to land 35; top up at the end rather than over-ordering.

## 8. Approve and report · **YOU** 15 min · **CLAUDE CODE** the rest

> Here's the CSV export from the responses sheet. Run the analysis, show me the excluded rows
> with reasons, then the verdict against the pre-registered criterion.

Work the exclusion list when approving. Then Claude Code writes the JK memo off the output.

---

# Still open, not blocking

- **Noah:** nonprofit fee, 25% vs 40%. Difference between ~$238 and ~$266, or between 7 and 8
  raters per pair. Should land before funding.
- **JK:** sign-off on the pre-registered criterion wording. Five-minute email that stops
  mattering the moment data exists.
- **Synthesia:** P1 and P4 new versions.

---

# Safety, plainly

**"Public repo" means** a stranger who found it could read the questions, the ten video IDs, the
endpoint address, and the completion code. They could **not** see anybody's answers (those live
in your Sheet, which was never in the repo), which video is old vs new (`decode_key.json`, which
git refuses), or anything touching Embrace's other systems. Worst case is someone watches a
training clip or posts a junk row you delete.

**The Apps Script permissions sound worse than they are.** The blast radius is one spreadsheet:
the script only appends, and never asked for access to your Drive or mail. It cannot read or
edit existing rows and is not a key to your Google account.

**Approve against the Sheet, not the completion code.** A fixed code is shareable by definition.
A real submission is a row carrying that participant's ID that clears the quality gates.

**Reject only on the objective gates** - didn't watch, wrong code word, impossible speed,
copy-pasted text. Never on someone's rating. CloudResearch participants talk, and unfair
rejections make your next study fill slower.

**The one accident to avoid:** editing `decode_key.example.json` (tracked by git) when you meant
`decode_key.json` (ignored). That file is the only thing keeping the study blind.

**Participant data** is a pseudonymous CloudResearch ID, the ratings, the comments, and
browser/screen/timezone for fraud checking. No names, no email, no IPs. Exports are gitignored.

---

# What it costs

| | |
|---|---|
| GitHub, YouTube, Google Sheets, ffmpeg, Python | $0 |
| CloudResearch dry run, 3 sessions | ~$21 |
| CloudResearch main run, 35 sessions | ~$245 |
| **Total** | **~$266** |
