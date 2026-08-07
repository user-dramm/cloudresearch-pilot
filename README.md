# CloudResearch pilot - rater instrument

Blind old-vs-new A/B on 5 course pairs, run on CloudResearch Connect. Connect recruits,
screens, and pays. This repo *is* the study: a single static page that plays the clips,
gates the questions behind real playback, and posts every answer to a Google Sheet.

**If you just want the ordered to-do list, read `START_HERE.md` instead.** This file is the
reference; that one is the runbook.

```
START_HERE.md                  ordered checklist: who does what, in what order
index.html                     the whole instrument (no build step, no framework)
config.js                      pair registry, YouTube IDs, gate settings   [PUBLIC]
apps_script/Code.gs            the Google Sheet endpoint
decode_key.example.json        template for the old/new mapping
decode_key.json                the real mapping                        [GITIGNORED]
analysis.py                    quality gates + PASS/FAIL vs the criterion
tools/make_fake_responses.py   synthetic data, so you can test the whole chain for $0
tools/check_sources.sh         pre-flight on the downloaded Synthesia files, before cutting
tools/make_clips.sh            ffmpeg: module 1 + 3 -> one clip, code word burned in
```

**Two video backends, one line of config.** `videoSource: "file"` serves your own MP4s
through a plain `<video>` tag; `videoSource: "youtube"` uses unlisted YouTube embeds. The
watch gate, the data schema, the Sheet, and `analysis.py` are byte-identical either way, so
this is not a decision that has to block anything - flip it later if you change your mind.

---

## How a response gets linked back to a specific video

This is the part worth reading slowly, because it is where blind studies usually break.

Every clip has an **opaque key** - `k5qd`, `k2wj` - invented for this study and meaningless
on its own. `config.js` maps a key to a YouTube ID. The private `decode_key.json` maps the
same key to `old` or `new`. Only the second file tells you which is which, and it never
goes in the repo.

```
config.js  (public)          decode_key.json  (private, local only)
  P2 / k5qd -> ytID_A          k5qd -> old,  code word "meadow"
  P2 / k2wj -> ytID_B          k2wj -> new,  code word "compass"
        |                            |
        +------------ row in the Sheet -------------+
          slot1_key = k2wj    (what they saw first)
          slot2_key = k5qd    (what they saw second)
          s1_overall = 4      (their rating of slot 1)
          h2h_choice_key = k2wj  (which one they picked)
```

The form records **positions**, not sides. It never knows, and never sends, the words
"old" or "new". `analysis.py` joins the key on the way out, at your desk. So even a
participant who opens DevTools cannot tell which video they're supposed to like, and
neither can anyone who clones the repo.

The chain also carries the honesty checks: `s1_codeword` proves they watched *that*
specific clip, `s1_watch_pct` proves how much of it actually played, `slot1_key` proves
which order they saw. All three land in the same row.

---

## Setup, in order

Roughly an hour, most of it waiting on uploads. Do steps 1–3 while the courses are still
rendering; only step 4 needs finished video.

### 1. Google Sheet + endpoint (15 min)

1. New Google Sheet, rename the first tab to `responses`.
2. **Extensions → Apps Script**, paste in `apps_script/Code.gs`, save.
3. **Deploy → New deployment → Web app.** Execute as **Me**; Who has access **Anyone**.
   (Connect workers are anonymous - "Anyone with a Google account" will lock them out.)
4. Copy the `/exec` URL. Open it in a browser: you should see `{"ok":true,...}`.
5. Paste it into `config.js` as `endpoint`.

Every redeploy issues a **new URL**. If you edit `Code.gs` later, use
**Manage deployments → edit the existing deployment → New version** so the URL survives.

### 2. Cut and host the clips (30 min, once the videos exist)

Cut module 1 + module 3 from each version and concatenate. Use the script for all ten, not
just some of them:

```bash
./tools/make_clips.sh k5qd meadow  old/00158_mod1.mp4 old/00158_mod3.mp4
./tools/make_clips.sh k2wj compass new/00158_mod1.mp4 new/00158_mod3.mp4
```

It normalises resolution, frame rate, and audio, encodes every clip through identical
settings, burns the code word in at the 45% mark, and sets `+faststart`. **The identical
encoding is methodological, not cosmetic.** Raters are scoring visual quality; if the old
clips get encoded differently from the new ones, some of what you measure is your encoder.
One script, ten runs, no hand-tuning.

#### Where to put them

At 720p a 10-minute clip lands around 100-150 MB, so ten clips is roughly 1.2 GB of
storage and about 10-12 GB of traffic across 38 sessions.

| | Storage fit | Traffic fit | Cost | Verdict |
|---|---|---|---|---|
| **Cloudflare R2** | 10 GB free | egress is free, always | $0 | **Recommended.** Public bucket, paste the URLs into `config.js`, done. |
| Backblaze B2 | 10 GB free | free via Cloudflare | ~$0 | Fine, slightly more setup. |
| Bunny.net | pennies | ~$0.01/GB | ~$0.15 | Fine, and a real CDN. |
| Netlify | works | 100 GB/mo free | $0 | Works, but 1.2 GB of binaries bloats the deploy. |
| GitHub Pages | ~1 GB soft cap | fine | $0 | **Don't.** The clips won't fit, and binaries in git history are permanent. |

Keep the HTML on Pages or Netlify and the video on R2. They're different problems.

#### If you use YouTube instead

Set `videoSource: "youtube"` and fill in `yt` instead of `src`. Then:

- Upload all 10 clips **in a single session on the same channel.** Upload dates, channel
  names, and description text are the classic way a blind study leaks - if five clips were
  posted today and five last year, a curious rater can tell which is which.
- **Unlisted.** Not private (won't embed), not public.
- Blind titles: `A-1`, `A-2`, `B-1`. No course name, no date, no version.
- Neutral thumbnails, no end screens, no cards.
- **Upload the night before, not an hour before launch.** YouTube processes the low
  resolutions first and HD later. A clip that looks fine to you at 360p may still be
  rendering at 720p when your raters hit it, and "the video was blurry" is feedback about
  YouTube's queue, not about your pipeline. Check each clip shows 720p in the quality menu
  before you point Connect at anything.
- Still use `tools/make_clips.sh` for the cut, the concat, and the code word. YouTube
  re-encodes what you give it, but its encoder is content-adaptive - feeding it ten
  identically-encoded masters keeps that variable as quiet as it can be.

#### Which backend is actually better here

Self-hosted MP4 wins on the two things this study is about:

- **Blinding.** No YouTube chrome, no channel name, no upload date, no "watch on YouTube"
  escape hatch, no related-video leakage. The metadata problem above simply stops existing.
- **Gate strength.** With `<video>` the form can *rewind* an attempt to scrub past the
  furthest point genuinely watched (`blockSeeking: true`). YouTube can only decline to
  credit skipped time - the rater still sees the ending.

YouTube wins on robustness: adaptive bitrate means a rater on poor wifi still gets through,
where a 120 MB progressive MP4 may stall. On a paid panel a stall is an abandoned session,
so this isn't nothing. It also needs zero infrastructure.

Given a US desktop-only panel on broadband, I'd take the blinding and run self-hosted, with
R2 in front of it. But the switch is one word in `config.js`, and if the dry run shows
buffering complaints you can flip to YouTube and relaunch the same afternoon.

### 3. `config.js` and `decode_key.json`

Fill in the clip URLs (or YouTube IDs) against the opaque keys, and flip `enabled: true` only for pairs
whose clips are genuinely live. Then:

```bash
cp decode_key.example.json decode_key.json
# fill in old/new and the code words - then confirm it will not be committed:
git check-ignore -v decode_key.json
```

Placeholder URLs containing `example.com` are treated as not-ready, so a half-filled pair
can never accidentally go live. Per the 7/30 build note, pairs 00051 and 00175 aren't
ready - leave them `enabled: false`;
the form silently excludes them and assigns raters across the live pairs only. Flip them on
when their clips land and the later wave pools into the same 35 votes.

### 4. Host it

**GitHub Pages** - free, HTTPS, nothing to sign up for beyond GitHub. Requires a **public**
repo; Pages on a private repo needs a paid GitHub plan. Public is fine: the decode key is
gitignored, and the YouTube IDs reach every participant's browser regardless of where the
code lives.

**Netlify** - the alternative if you want the repo private anyway. Free plan, no credit
card, deploys straight from a private GitHub repo.

```bash
git init && git add . && git commit -m "Pilot instrument v1.0.0"
git branch -M main
git remote add origin git@github.com:<org>/<repo>.git
git push -u origin main
# Settings -> Pages -> Deploy from branch -> main / (root)
```
URL: `https://<org>.github.io/<repo>/`

**Netlify** - pick this instead if you'd rather keep the repo private. Free tier serves
from a private GitHub repo; connect the repo, no build command, publish directory `/`.
Drag-and-drop deploy also works if you'd rather not connect anything.

### 5. Test before you spend anything

```
https://<your-url>/?participantId=TEST001&selftest=1&pair=P2
```

`selftest=1` tags the row so `analysis.py` drops it automatically. `pair=P2` forces a
specific pair so you can walk each one. Confirm: the gate fills only while the video is
actually playing, skipping ahead earns no credit, questions unlock at 90%, the code word
field works, and a row lands in the Sheet with the completion code.

Then test the analysis side without spending a cent:

```bash
python3 tools/make_fake_responses.py --true-pref 0.80 --out fake.csv
python3 analysis.py fake.csv --key decode_key.json     # should read VALIDATED
python3 tools/make_fake_responses.py --true-pref 0.50 --out null.csv --seed 3
python3 analysis.py null.csv --key decode_key.json     # should read NOT VALIDATED
```

Running both directions is the cheap proof that the gate isn't rigged - worth showing JK.

### 6. The Connect study

Field-by-field copy is already written in `Cloud_Research_Connect_Form_Copy.md`. Two things
to get right in the Connect UI:

- **Project URL**: your Pages URL. Connect appends `?participantId=…`; the form reads it.
  If your URL already has a query string, Connect appends with `&` - test the exact link
  Connect generates before launching.
- **Completion method**: set a *fixed* completion code matching `completionCode` in
  `config.js`. Connect disallows `0`, `1`, `I` and `O` in fixed codes - `EMBR7K2QX4` is
  clean. Also copy the **Redirect URL** from the end of the Create-a-Study wizard into
  `redirectUrl`; Connect treats the redirect as the more reliable method, and the form
  will use it while still showing the code as a fallback.
- **Devices**: desktop and laptop only. Mobile breaks the watch gate.
- **Exclude previous participants** if you run the dry run as a separate study, so the
  same three people can't take the main run.

---

## Git safety

The repo is served to the public, so treat everything in it as published.

**Never commit**
- `decode_key.json` - it is the entire blind.
- Any CSV or export. Participant IDs are pseudonymous but they are still subject data, and
  a repo is the wrong place for them. `.gitignore` covers `*.csv` and `responses*`.
- Credentials of any kind. The one URL that *must* be public is the Apps Script endpoint.

**About that endpoint.** It ships in client-side JS, so it is public by construction. The
`formToken` in `config.js` keeps drive-by bots out; it is not security and shouldn't be
described as such. The real protections are structural: the script only ever *appends*, it
cannot read or edit existing rows, and junk rows are trivially deleted. Don't put anything
confidential in that Sheet.

**Tag what you launch.** This is what makes the pre-registration mean something:

```bash
git tag -a dryrun-v1.0.0 -m "Instrument as launched for the 3-session dry run"
git tag -a mainrun-v1.0.0 -m "Instrument as launched for the 35-session main run"
git push --tags
```

Bump `FORM_VERSION` in `index.html` alongside the tag. It is written into every row, so any
row can be traced to the exact code that produced it. If you change a question mid-study,
the version field is the only thing that will tell you which rows are comparable.

**Don't rewrite history after launch.** No `push --force`, no amending launched commits. The
audit trail is a deliverable here, not housekeeping. Commit each `config.js` video-ID change
separately so you can prove which clips were live when.

**If you accidentally commit the decode key**, deleting it in a later commit is not enough -
it stays in history. Rotate instead: invent new opaque keys in `config.js` and
`decode_key.json`, re-upload nothing, and treat the old keys as burned.

---

## Reading the results

Export the `responses` tab to CSV, then:

```bash
python3 analysis.py responses.csv --key decode_key.json
```

It applies the quality gates first and lists every excluded row with the reason - that list
is what you work from when approving or rejecting on Connect. Then it prints the three
pre-registered clauses separately, plus diagnostics that aren't part of the criterion:
position effect, the speaker findings, preference magnitude, and inter-rater agreement.

### How the questions are ordered, and why it isn't arbitrary

**Current shape, as of 2026-08-07.** Per video: **four labelled 1-5 scales** and nothing
else, five clicks-per-video including the code word. Every open question sits at the end
of the study, not in the per-video block.

| Per video | |
|---|---|
| `overall` | Overall, how would you rate this training video? |
| `audio` | The narration, the voice and how it was delivered |
| `visuals` | The slides and what was on screen |
| `clarity` | How well the information was explained |
| `audio_why` | shown **only** if `audio` was 1 or 2, and optional even then |
| code word | a text box under the player, outside the locked card |

Two earlier questions are gone, and the reasons are worth keeping:

- **A separate speaker question** overlapped the narration rating almost entirely, so raters
  answered the same thing twice.
`clarity` has a history worth knowing. It shipped as the question "How well did it explain
things?", was dropped on 2026-08-07 for reading out of place, and came back the same day
reworded once the reason was clear: the problem was **register, not construct**. The other
three are plain labels, so a question among them interrupted the run of clicks. As a label
it reads as one of the set.

Two wording decisions inside it:

- **"Explained", not "presented".** The narration and the on-screen questions *are* the
  presentation, so a presentation metric would mostly re-ask them in summary and return a
  number that moves with them and discriminates nothing. "Explained" asks whether the
  material landed, which two videos can differ on while sharing identical voice quality and
  identical slides, because it is carried by structure, pacing and examples. That is what
  the recreation changed.
- **Not "the content itself".** Both videos in a pair teach the same course from the same
  scope, so content barely differs. Asking about content invites a rating of the subject
  matter, identical on both sides, and that noise would land in the same column as the
  signal.

The field id stays `clarity` although the question says "explained", because the id is older
than the wording and every reader resolves it through `field()`.

> **Correction.** An earlier version of this file claimed the deployed Apps Script already
> had `s1_clarity` / `s2_clarity` columns. It did not. See *The Sheet columns had drifted*
> below.

What the ordering still buys:

- **Every scale point is labelled in words**, not a digit with only the ends named. Fully
  labelled scales have higher test-retest reliability, and the gain is largest among
  respondents with less formal education, which is this panel. The submitted value is still
  1-5, so nothing in the analysis changes.
- **No question anywhere names what is being tested.** The conditional narration follow-up is
  a free text box, not a list we supplied, so "it sounded robotic" is **volunteered rather
  than prompted** - reached only by a rater who has already scored the narration low.
  `analysis.py` scans the free text for words like *robotic* or *monotone* on word boundaries;
  matching `ai` as a substring would hit "said", "aid" and "explain".

The head-to-head stays a **forced binary choice** with no tie option: paired comparison is
more discriminative than rating each video alone, and clauses 1 and 2 are computed from that
one field. A tie option would create a third category the binomial cannot consume. Instead
the follow-up asks **how much better**, which is how a genuine tie gets recorded - and
`analysis.py` re-runs the pooled preference excluding everyone who said "barely any
difference", as the honest check on how much of the margin is coin-flips.

The gates it enforces: selftest rows, rows from another study tag, missing or duplicate
participant IDs, under 85% watched on either clip, a wrong code word, playback faster than
1.25x, a missing head-to-head choice, and a session shorter than 85% of the two clips
combined. **There is deliberately no text-length gate.** Every open question is optional, so
a length gate would exclude the entire cohort; that mistake was made twice and caught both
times by re-running the analysis with all free text blanked (35/35 still pass). That last one is **derived from the row**, not fixed: `s1_duration_sec` and
`s2_duration_sec` ride along in every response, so the floor tracks whatever was actually
served. The flat 480 s remains only as a backstop for rows where duration failed to record.
`--include-excluded` re-runs with all rows as a sensitivity check - if the verdict flips
when you include the junk, that belongs in the writeup.

**Read the thresholds honestly.** The locked criterion says "≥65% AND exact binomial
p < .05". At n = 35 those two clauses only both hold from **24 wins (68.6%) up**; exactly
65% is not significant. The script prints that number so nobody has to rediscover it after
the data lands.

**Clause 1 needs five pairs to be satisfiable at all.** "New ahead in ≥ 4 of 5 pairs" cannot
be met by a three-pair wave, however lopsided the result: three pairs won out of three is
still 3, and 3 < 4. A synthetic three-pair run at 80% preference, winning every pair, prints
NOT VALIDATED - see `proof/analysis_gate_proof.txt` for the shape of the output. So either all
five pairs run before the verdict is read, or clause 1 gets restated **with JK, before any
data exists**. Restating it afterwards is moving the goalposts, and it would void the point of
pre-registering.

---

## The Sheet columns had drifted, and what you must do about it

Found 2026-08-07 by comparing what the form sends against `HEADERS` in the Apps Script.
They had come apart in both directions:

- **12 real answers had no column** and were being written into the `extra_json` blob:
  both clarity ratings, `h2h_magnitude` (which the "barely any difference" sensitivity
  check reads), `standby`, both `audio_why` follow-ups, `assignment_id`, `project_id`,
  `resumed_from_save` and the video counts.
- **15 columns sat permanently blank**, left from an earlier question set: `pacing`,
  `ai_read`, per-section `errors` and `standby`, the paste counters, `h2h_confidence`.

**Nothing was ever lost.** `analysis.py`, `decode_responses.py` and `make_report.py` all
read through a `field()` helper that unpacks the overflow, so every number reached the
analysis correctly. But the Sheet is the view used to eyeball a rater before approving
payment, and it showed blank columns with the answers buried in JSON.

`HEADERS` is now rewritten to exactly one column per answer: 62 columns, none blank, none
duplicated. `tools/test_headers.js` asserts that and fails if they ever drift again.

### Applying it (do this BEFORE launch, not during)

Rows are written positionally as `HEADERS.map(...)`, and the header row is created only
once. So reordering or inserting columns mid-study writes new rows against the **old**
header row and silently misaligns every column in them. That makes this safe only while
the sheet has no real data, which is now.

1. Open the Apps Script project bound to the responses Sheet.
2. Replace the `HEADERS` array with the one in `apps_script/Code.gs`, and take the
   `token` line in the overflow loop with it.
3. **Deploy > Manage deployments > edit the existing deployment > Deploy.** Editing the
   existing one keeps the URL, which is what `config.js` points at. Do not create a new
   deployment, or the endpoint URL changes and every rater hits a dead form.
4. In the responses tab, delete **every row including the header row**. The script writes
   a fresh header row on the next submission.
5. Submit once through the form and confirm the new columns appear with values in them.

Until step 3 is done, clarity and the rest still arrive in `extra_json` and the analysis
still reads them correctly. It is a readability fix, not a data-integrity one.

## Captions, and a visible difference between the two sides

Two separate things came out of checking this, and the second matters more.

### 1. YouTube's caption layer was leaking through, and is now stopped

Every upload has a YouTube auto-generated ASR track. Screenshots of all ten videos showed
that layer rendering despite `cc_load_policy:0` and `unloadModule`, because the unload ran
once at `onReady` and the module can load again afterwards. On the recreation side, which
has captions burned into the picture, that produced TWO overlapping caption blocks,
differently wrapped, unreadable. On the archive side it produced a caption track that
should not have been there at all.

`killCaptions()` now applies three mechanisms on `onReady` AND on every state change:
`cc_load_policy:0`, `unloadModule`, and `setOption(track, {})`. Re-screenshotted all ten
afterwards: YouTube's layer is gone from every one.

**You cannot fix this in YouTube Studio.** Studio lets you delete tracks you uploaded, but
there is no delete for an auto-generated one. An earlier version of this file suggested
disabling it there; that was wrong. The code is the fix.

Note that `getOptions()` still reports `["captions"]` after the fix. The module is present
but no track is selected, so that reading means nothing. Only a screenshot settles it.

### 2. The recreation has burned-in subtitles. The archive has none.

This is not a bug and not a player setting. It is a real difference between the two builds,
and it is the most visible difference a rater will see:

| | captions on screen |
|---|---|
| Archive (old) | none |
| Recreation (new) | burned in, throughout |

The recreated pipeline genuinely produces captioned video, so this is something it improved.
But it is worth naming before any data exists, because **a rater who prefers the recreation
may be preferring the subtitles** rather than the narration, the slides or the explanation,
and the `visuals` scale in particular will absorb it.

Nothing here needs changing. Removing the burned-in captions would mean re-rendering and
re-uploading five videos, and it would also mean testing a version of the pipeline you do
not actually ship. The right move is to record it now, as a known contributor to any gap,
rather than discover it in the write-up. If the criterion is being restated with JK anyway,
this belongs in that conversation.

## Resume, and why the demo deliberately does not have it

A rater who loses power, closes the tab, or gets bumped off wifi reopens the same link
on the same computer and carries on: answers, watch credit and elapsed time all come
back. Elapsed time matters as much as the rest, because `analysis.py` rejects a session
shorter than 85% of the video it served, and without carrying it across a reload an
honest rater would be failed for having recovered.

Saved state is keyed on the participant id: `embr_pilot_<studyTag>_<PID>`. Connect gives
every rater a distinct id, so each gets a private slot and nobody can land in anyone
else's session.

**The demo has resume switched off, on purpose.** A preview has no participant id, so
the key falls back to `..._anon` - one key shared by everyone who opens it. That is fine
for a single rater and wrong for a link that gets passed around: two people on one
machine, or one person handing a laptop to a colleague, would both be `anon`, so the
second would be dropped into the first person's half-finished session with the ratings
pre-filled and the watch gate already cleared. It would also leave a reviewer unable to
take a second look. So a preview build never reads or writes saved state and clears any
residue on load. Gated on `CFG.demoBanner`, which only `demo/config.js` sets.

Verified end to end, both directions:

| | real study | demo |
|---|---|---|
| person 1 answers and walks away | 936 bytes written under `..._<PID>` | **nothing written** |
| person 2 reopens on that machine | resumes, answers and credit restored | **clean intro screen, 0 saved keys** |

Two related things checked and deliberately left alone:

- **`furthest` and `last` are not persisted.** On resume the player restarts at 0, so a
  restored `furthest` of 0 matches the real position and no spurious anti-skip rewind
  fires. Persisting them would be strictly worse.
- **`loadSaved()` refuses to resume into a different pair.** If assignment ever handed a
  returning rater another pair, their saved answers describe other videos, and merging
  them would mislabel the row. The guard is right and stays.

### Resume used to be intermittent, and silently so

The worse bug testing found. Saved state is only merged back if the assigned pair still
matches (`loadSaved()`), and the pair was re-derived from scratch on every visit. The
endpoint hands out whichever pair has the fewest raters; the offline fallback picks
`hash(pid) % live.length`. **Those two disagree in general.** So a rater whose first
visit reached the endpoint but whose return visit hit its roughly 1-in-4 failure rate got
a *different* pair, the guard correctly refused to merge answers describing other videos,
and they lost the session - resume failing precisely when the network is bad enough to
need it. Seen live: two runs of the same test, one resumed, one did not.

Worse, `nth` was not saved either, and the A/B order is `nth % 2`. A fallback on the
return visit could therefore seat the two versions **the other way round**, and the
restored section-1 answers would then describe the other video. That mislabels a row
rather than losing it, which is far worse: the study would report a preference in the
wrong direction and look perfectly valid doing it.

Both fixed. `assign()` now checks for a saved session *before* asking the endpoint
anything, and honours its pair and its `nth`: a returning rater's pair is already decided
because they have watched those videos. Nothing is asked of the endpoint on that path -
the assignments row already exists, so there is no slot to claim. Proved with the
endpoint **completely dead** (every request to it aborted):

```
VISIT 1 (endpoint healthy)   pair=P4  order=k1ps>k6hb  nth=1  watched=40s  label=8%
  >>> power cut
VISIT 2 (endpoint DEAD)      pair=P4  order=k1ps>k6hb  nth=1  watched=39s  label=8%
  same pair YES   same A/B order YES   credit carried YES   shown on screen YES
```

A resumed row is identifiable by `resumed_from_save` in the `extra_json` column.
`assign_source` deliberately still reports how the pair was *originally* chosen, because
`applySaved()` restores the whole of `D`; that is the field balance is audited from.

One further bug, now fixed: `applySaved()` repainted the gate bar only for videos
that had fully cleared it, so someone resuming part-way through saw **0%** even though
their credit was intact - the snapshot held `{"watched":44.18,"duration":546}` and came
back as 44s in memory. The credit was never lost, but a rater cannot read memory. They
see 0% and conclude they have to rewatch nine minutes, which is exactly what resume
exists to prevent.

## Pair assignment

`doGet(?action=assign)` in `Code.gs` hands out whichever pair has the fewest raters so far,
counting completed responses plus assignments from the last 45 minutes that haven't completed.
It also returns `nth`, which the form uses to alternate A/B order within the pair. The
`assignments` tab records every handout.

### Measured, not claimed

An earlier version of this file said the balancer keeps every pair within one rater of even in
"~91% of simulated runs". **It does not.** Re-simulated 4,000 times with 20% abandonment and
the real 45-minute pending window:

| Scenario | Within 1 of even | Mean smallest cell | A pair left <=4 |
|---|---|---|---|
| Per-browser random, 35 launched | 1% | 3.0 | 93% |
| Balanced, 35 launched | 72% | 5.0 | 21% |
| Balanced, endpoint failing 25% | 51% | 4.8 | 27% |
| Balanced + 3x retry, 35 launched | 70% | 5.0 | 21% |
| **Balanced + retry, 44 launched** | 67% | **6.4** | **0.7%** |

The design is well justified - random assignment is a disaster, and worse than the old figure
admitted - but the specific 91% was wrong, so it is corrected here rather than repeated.

**Launch about 44, not 35.** Connect pays only completions, so ordering 35 lands roughly 28,
and at 28 completions some pair sits at 4 raters or fewer in a fifth of runs. Clause 1 asks
whether new is ahead *within each pair*; four raters cannot answer that. Launching ~44 to land
~35 puts the smallest cell at 6.4 on average and a thin pair under 1%.

**The retry matters.** This deployment returns Google's HTML error page instead of JSON on
roughly one anonymous request in four ON THE DAY IT WAS MEASURED. Re-measured 2026-08-07 it
was 0 failures in 20, so treat the rate as variable rather than fixed - and note the original
figure may have been inflated by not following the 302 redirect Apps Script issues, which
makes a healthy call look like a failure. The retry stays either way: it is three cheap
attempts against a dependency that has been seen to fail. Every failure drops that rater onto the local hash, and
at a 25% failure rate balance falls from 72% to 51%. `assign()` therefore retries three times,
which restores it to 70%. Retrying is safe because the endpoint returns a participant's
existing assignment (`repeat: true`) rather than issuing a second one.

If the call fails all three times the form falls back to a local hash and records
`assign_source: local`, so you can tell from the data whether balancing was in effect for any
given row.

Two known limits, both visible in the data rather than hidden:

- `nth` (which drives A/B order) is the pair's count at assignment time, so an abandoned
  session can hand the same `nth` to the next rater and repeat an order. `analysis.py` reports
  the position effect, which is where that would show up.
- `?pair=P3` on the URL overrides everything. That is how you force a pair for testing, and it
  records `assign_source: forced`, so a row that used it is identifiable.

Reproduce any of the above with `tools/assign_sim.py`.

## Reusing this for the monthly program

The monthly design is monadic-plus-anchor rather than paired, so:

- `config.js` becomes one entry per new course plus one permanent `anchor` entry. If you
  self-host, the anchor clip stays at one fixed URL for 2-3 quarters - do not re-encode it,
  since a re-encode silently changes the benchmark everything is normalised against.
- `index.html` drops the head-to-head screen and shows two clips - the course and the
  anchor - in randomised order.
- `analysis.py` swaps the binomial for anchor-normalised scoring: subtract each rater's
  anchor score from their course score, then test against the benchmark bar.

Everything else - the gate, the code words, the endpoint, the Sheet, the hosting, the git
discipline - carries over unchanged. That reuse is a real part of the pilot's value: the
$266 buys the instrument as well as the answer.
