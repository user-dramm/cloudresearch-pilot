#!/usr/bin/env python3
"""
Generate a synthetic responses.csv so analysis.py can be tested end to end
before any real money is spent.

    python3 tools/make_fake_responses.py --true-pref 0.75 --out fake.csv
    python3 analysis.py fake.csv --key decode_key.json

--true-pref is the real underlying probability a rater prefers the new version.
Run it at 0.50 to confirm the criterion correctly FAILS on noise, and at 0.80 to
confirm it PASSES on a genuine win. That is the sanity check that the gate is not
rigged in either direction.
"""
import argparse, csv, json, random

HEADERS = None  # taken from apps_script/Code.gs ordering at runtime


def build_headers():
    h = ["row_id", "ts_server", "ts_client", "study_tag", "form_version", "is_selftest",
         "participant_id", "pair_id", "cc_code", "video_source", "slot1_key", "slot2_key"]
    for s in ("1", "2"):
        h += ["s%s_%s" % (s, f) for f in
              ("overall", "visuals", "audio", "clarity", "errors", "errors_detail",
               "speaker", "speaker_issues", "speaker_other", "speaker_distract",
               "codeword", "comment", "watched_sec", "duration_sec", "watch_pct",
               "seek_fwd", "seek_back", "load_errors", "max_rate", "rate_ms", "paste_count")]
    h += ["h2h_choice", "h2h_choice_slot", "h2h_choice_key", "h2h_magnitude", "h2h_why",
          "standby", "h2h_other", "paste_count", "assign_source", "assign_nth", "total_ms",
          "completion_code", "user_agent",
          "screen_w", "screen_h", "tz", "referrer", "extra_json"]
    return h


# The old ai_read question is gone. A rater now says how the speaker was, and only
# those who flag a problem see a tick-any list of what was wrong. These strings must
# match index.html, and SPEAKER_FLAG / FAKE_OPTION in analysis.py.
SPK_GOOD = "The speaker did well"
SPK_OK   = "The speaker was okay"
SPK_OFF  = "Something seemed off about the speaker"
ISSUES   = ["Flat or monotone", "Odd pauses or rhythm", "Mispronounced a word",
            "Volume went up and down", "Hard to make out some words", "Sounded fake"]
MAGNITUDE = ["Barely any difference", "Slightly better", "Clearly better", "Much better"]
STANDBY   = ["Yes, no reservations", "Yes, with some reservations", "No"]
COMMENT = ("The slides were clear and the narrator was easy to follow throughout, "
           "though a couple of sections felt a little rushed near the end.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default="decode_key.json")
    ap.add_argument("--out", default="fake.csv")
    ap.add_argument("--per-pair", type=int, default=7)
    ap.add_argument("--true-pref", type=float, default=0.75)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--score-gap", type=float, default=None,
                    help="mean 1-5 'overall' advantage for new; defaults to a value "
                         "consistent with --true-pref, so --true-pref 0.5 is a true null")
    a = ap.parse_args()
    random.seed(a.seed)
    gap = a.score_gap if a.score_gap is not None else max(0.0, (a.true_pref - 0.5) * 3.2)

    key = json.load(open(a.key))["keys"]
    pairs = {}
    for k, v in key.items():
        pairs.setdefault(v["pair"], {})[v["version"]] = (k, v.get("codeword", ""))

    headers = build_headers()
    rows = []
    i = 0
    for pair, sides in sorted(pairs.items()):
        if "old" not in sides or "new" not in sides:
            continue
        for _ in range(a.per_pair):
            i += 1
            new_first = random.random() < 0.5
            slot = {1: "new" if new_first else "old", 2: "old" if new_first else "new"}
            prefers_new = random.random() < a.true_pref
            harsh = random.choice([-0.5, 0, 0, 0.5])   # rater leniency
            r = dict.fromkeys(headers, "")
            r.update({
                "row_id": "RFAKE%03d" % i, "ts_server": "2026-07-31T12:00:00Z",
                "ts_client": "2026-07-31T11:58:00Z", "study_tag": "pilot-2026-07",
                "form_version": "1.0.0", "is_selftest": "no",
                "participant_id": "CR%05d" % i, "pair_id": pair, "cc_code": "EMBR-CC-XXXXX",
                "slot1_key": sides[slot[1]][0], "slot2_key": sides[slot[2]][0],
                # Must match the h2h_choice options in index.html. Each side is one
                # video in two parts - one version of the course.
                "h2h_choice": "The first video" if (slot[1] == "new") == prefers_new else "The second video",
                "h2h_choice_slot": 1 if (slot[1] == "new") == prefers_new else 2,
                "h2h_choice_key": sides["new" if prefers_new else "old"][0],
                "h2h_why": "The second one held my attention better and the audio was cleaner.",
                # Magnitude tracks how real the effect is, so a true null produces
                # mostly "barely any difference" and the sensitivity check in
                # analysis.py has something to bite on.
                "h2h_magnitude": random.choice(
                    MAGNITUDE[1:] if a.true_pref > 0.6 else MAGNITUDE[:2]),
                "standby": random.choice(STANDBY[:2] if prefers_new else STANDBY),
                "total_ms": random.randint(1_200_000, 1_900_000),
                "completion_code": "EMBR7K2QX4", "user_agent": "Mozilla/5.0 fake",
                "screen_w": 1920, "screen_h": 1080, "tz": "America/Chicago",
            })
            for s in (1, 2):
                side = slot[s]
                base = 3.1 + (gap if side == "new" else 0.0) + harsh
                r["s%d_overall" % s] = max(1, min(5, round(random.gauss(base, 0.7))))
                for f, off in (("visuals", .1), ("audio", .2), ("clarity", -.1)):
                    r["s%d_%s" % (s, f)] = max(1, min(5, round(random.gauss(base + off, 0.8))))

                # Speaker block. The old side flags problems more often, and only a
                # flagged row gets the probe fields - exactly as the form behaves,
                # so analysis.py is exercised on realistically sparse data.
                # The new side flags less often but not never - if it never did, the
                # new-side diagnostics would print 0% and we would not know whether
                # that is the data or a bug in the analysis.
                spk = random.choice([SPK_GOOD, SPK_GOOD, SPK_GOOD, SPK_OK, SPK_OFF]
                                    if side == "new"
                                    else [SPK_OK, SPK_OFF, SPK_OFF])
                r["s%d_speaker" % s] = spk
                if spk == SPK_OFF:
                    picks = random.sample(ISSUES, random.randint(1, 3))
                    r["s%d_speaker_issues" % s] = "; ".join(picks)
                    r["s%d_speaker_distract" % s] = random.choice(["No", "A little", "Yes, a lot"])
                    if random.random() < 0.3:
                        r["s%d_speaker_other" % s] = "The voice sounded robotic to me."

                r["s%d_errors" % s] = random.choice(
                    ["No, nothing I noticed"] * (4 if side == "new" else 2) + ["Yes, one or two"])
                r["s%d_codeword" % s] = sides[side][1]
                r["s%d_comment" % s] = COMMENT
                dur = 600
                r["s%d_duration_sec" % s] = dur
                r["s%d_watched_sec" % s] = int(dur * random.uniform(.9, 1.0))
                r["s%d_watch_pct" % s] = round(r["s%d_watched_sec" % s] / dur, 3)
                r["s%d_seek_fwd" % s] = random.choice([0, 0, 0, 1])
                r["s%d_seek_back" % s] = 0
                r["s%d_load_errors" % s] = 0
                r["s%d_rate_ms" % s] = random.randint(120_000, 300_000)
                r["s%d_paste_count" % s] = 0
            rows.append(r)

    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)
    print("wrote %d synthetic rows to %s (true preference for new = %.2f)"
          % (len(rows), a.out, a.true_pref))


if __name__ == "__main__":
    main()
