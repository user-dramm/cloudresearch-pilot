# CloudResearch pilot — rater instrument

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

Every clip has an **opaque key** — `k5qd`, `k2wj` — invented for this study and meaningless
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
   (Connect workers are anonymous — "Anyone with a Google account" will lock them out.)
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
  re-encodes what you give it, but its encoder is content-adaptive — feeding it ten
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
# fill in old/new and the code words — then confirm it will not be committed:
git check-ignore -v decode_key.json
```

Placeholder URLs containing `example.com` are treated as not-ready, so a half-filled pair
can never accidentally go live. Per the 7/30 build note, pairs 00051 and 00175 aren't
ready - leave them `enabled: false`;
the form silently excludes them and assigns raters across the live pairs only. Flip them on
when their clips land and the later wave pools into the same 35 votes.

### 4. Host it

**GitHub Pages** — free, HTTPS, nothing to sign up for beyond GitHub. Requires a **public**
repo; Pages on a private repo needs a paid GitHub plan. Public is fine: the decode key is
gitignored, and the YouTube IDs reach every participant's browser regardless of where the
code lives.

**Netlify** — the alternative if you want the repo private anyway. Free plan, no credit
card, deploys straight from a private GitHub repo.

```bash
git init && git add . && git commit -m "Pilot instrument v1.0.0"
git branch -M main
git remote add origin git@github.com:<org>/<repo>.git
git push -u origin main
# Settings -> Pages -> Deploy from branch -> main / (root)
```
URL: `https://<org>.github.io/<repo>/`

**Netlify** — pick this instead if you'd rather keep the repo private. Free tier serves
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

Running both directions is the cheap proof that the gate isn't rigged — worth showing JK.

### 6. The Connect study

Field-by-field copy is already written in `Cloud_Research_Connect_Form_Copy.md`. Two things
to get right in the Connect UI:

- **Project URL**: your Pages URL. Connect appends `?participantId=…`; the form reads it.
  If your URL already has a query string, Connect appends with `&` — test the exact link
  Connect generates before launching.
- **Completion method**: set a *fixed* completion code matching `completionCode` in
  `config.js`. Connect disallows `0`, `1`, `I` and `O` in fixed codes — `EMBR7K2QX4` is
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
- `decode_key.json` — it is the entire blind.
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

**If you accidentally commit the decode key**, deleting it in a later commit is not enough —
it stays in history. Rotate instead: invent new opaque keys in `config.js` and
`decode_key.json`, re-upload nothing, and treat the old keys as burned.

---

## Reading the results

Export the `responses` tab to CSV, then:

```bash
python3 analysis.py responses.csv --key decode_key.json
```

It applies the quality gates first and lists every excluded row with the reason — that list
is what you work from when approving or rejecting on Connect. Then it prints the three
pre-registered clauses separately, plus diagnostics that aren't part of the criterion:
position effect, the speaker findings, preference magnitude, and inter-rater agreement.

### How the questions are ordered, and why it isn't arbitrary

The per-video block is a funnel: one broad open question, then the rating scales, then the
speaker block last. Three deliberate choices, each fixing a measurable defect:

- **The open question comes first.** When closed questions on a topic are asked first,
  respondents echo those concepts back in the later open answer — so an open question placed
  after them measures our prompt rather than their reaction.
- **Every scale point is labelled in words**, not shown as a digit with only the ends named.
  Fully labelled scales have higher test–retest reliability, and the gain is largest among
  respondents with less formal education — which is this panel. The submitted value is still
  1–5, so nothing in this script changes.
- **The speaker block is last, and nothing follows it.** "Sounded fake" is the only option in
  the form that reveals what the study tests. It is reached only by a rater who has already
  said something seemed off, from a tick-any list whose order is randomised (early options in
  such lists get picked disproportionately) with the other-specify row pinned last.

That makes **reads-as-fake an unprompted measure**, which is why it is worth more than the
old "did this sound computer-generated?" checkbox it replaced. `analysis.py` also scans the
free text for volunteered words like *robotic* or *monotone*, matched on word boundaries —
matching `ai` as a substring would hit "said", "aid" and "explain".

The head-to-head stays a **forced binary choice** with no tie option: paired comparison is
more discriminative than rating each video alone, and clauses 1 and 2 are computed from that
one field. A tie option would create a third category the binomial cannot consume. Instead
the follow-up asks **how much better**, which is how a genuine tie gets recorded — and
`analysis.py` re-runs the pooled preference excluding everyone who said "barely any
difference", as the honest check on how much of the margin is coin-flips.

The gates it enforces: selftest rows, missing or duplicate participant IDs, under 85%
watched on either clip, a wrong code word, a comment under 40 characters, playback faster
than 1.25x, a missing head-to-head choice, and a session shorter than 85% of the two clips
combined. That last one is **derived from the row**, not fixed: `s1_duration_sec` and
`s2_duration_sec` ride along in every response, so the floor tracks whatever was actually
served. The flat 480 s remains only as a backstop for rows where duration failed to record.
`--include-excluded` re-runs with all rows as a sensitivity check — if the verdict flips
when you include the junk, that belongs in the writeup.

**Read the thresholds honestly.** The locked criterion says "≥65% AND exact binomial
p < .05". At n = 35 those two clauses only both hold from **24 wins (68.6%) up**; exactly
65% is not significant. The script prints that number so nobody has to rediscover it after
the data lands.

**Clause 1 needs five pairs to be satisfiable at all.** "New ahead in ≥ 4 of 5 pairs" cannot
be met by a three-pair wave, however lopsided the result: three pairs won out of three is
still 3, and 3 < 4. A synthetic three-pair run at 80% preference, winning every pair, prints
NOT VALIDATED — see `proof/analysis_gate_proof.txt` for the shape of the output. So either all
five pairs run before the verdict is read, or clause 1 gets restated **with JK, before any
data exists**. Restating it afterwards is moving the goalposts, and it would void the point of
pre-registering.

---

## Pair assignment

`doGet(?action=assign)` in `Code.gs` hands out whichever pair has the fewest raters so far,
counting completed responses plus assignments from the last 45 minutes that haven't completed.
It also returns `nth`, which the form uses to alternate A/B order within the pair. The
`assignments` tab records every handout.

Per-browser random assignment leaves a pair with <=4 raters about 61% of the time at n=35; the
balanced version keeps every pair within one rater of even in ~91% of simulated runs. If the
call fails the form falls back to a local hash and records `assign_source: local`, so you can
tell from the data whether balancing was in effect for any given row.

`?pair=P3` on the URL overrides everything, which is how you force a specific pair for testing
or run five separate exactly-balanced studies if you'd rather.

## Reusing this for the monthly program

The monthly design is monadic-plus-anchor rather than paired, so:

- `config.js` becomes one entry per new course plus one permanent `anchor` entry. If you
  self-host, the anchor clip stays at one fixed URL for 2-3 quarters — do not re-encode it,
  since a re-encode silently changes the benchmark everything is normalised against.
- `index.html` drops the head-to-head screen and shows two clips — the course and the
  anchor — in randomised order.
- `analysis.py` swaps the binomial for anchor-normalised scoring: subtract each rater's
  anchor score from their course score, then test against the benchmark bar.

Everything else — the gate, the code words, the endpoint, the Sheet, the hosting, the git
discipline — carries over unchanged. That reuse is a real part of the pilot's value: the
$266 buys the instrument as well as the answer.
