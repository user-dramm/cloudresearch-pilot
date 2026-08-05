#!/usr/bin/env python3
"""
The one correctness property that would ruin the study silently.

    python3 tools/test_attribution.py --key decode_key.json

Raters see the two versions in alternating order, because the first video is judged
in a vacuum and the second against the first. That alternation is necessary, and it
introduces exactly one way to get everything backwards: if a rating given to the
video in position 1 were credited to a fixed version rather than to whatever
actually played there, then every rater who saw the archive first would have their
scores attributed to the recreation and vice versa. Half the data would be inverted,
the effect would cancel toward zero, and NOTHING in the output would look wrong.

So this constructs two raters who hold the SAME opinion but saw the pair in OPPOSITE
orders, and asserts the analysis reaches the same conclusion for both. If attribution
ever breaks, the delta collapses and this fails.

Standard library only. Exits non-zero on failure.
"""

import argparse, csv, json, os, subprocess, sys, tempfile

HEADERS = ["row_id","ts_server","ts_client","study_tag","form_version","is_selftest",
           "participant_id","pair_id","cc_code","video_source","slot1_key","slot2_key"]
for _s in ("1", "2"):
    HEADERS += ["s%s_%s" % (_s, f) for f in
                ("overall","visuals","audio","pacing","errors","errors_detail","speaker",
                 "speaker_issues","speaker_other","speaker_distract","codeword","comment",
                 "watched_sec","duration_sec","watch_pct","seek_fwd","seek_back",
                 "load_errors","max_rate","rate_ms","paste_count")]
HEADERS += ["h2h_choice","h2h_choice_slot","h2h_choice_key","h2h_magnitude","h2h_why",
            "standby","h2h_other","paste_count","assign_source","assign_nth","total_ms",
            "completion_code","user_agent","screen_w","screen_h","tz","referrer","extra_json"]

LOW, HIGH = 2, 5          # the opinion: archive poor, recreation excellent


def build_row(pid, slot1, slot2, keys, winner_key, winner_slot, pair, cc):
    r = dict.fromkeys(HEADERS, "")
    r.update({"row_id": pid, "study_tag": "pilot-2026-07", "form_version": "test",
              "is_selftest": "no", "participant_id": pid, "pair_id": pair, "cc_code": cc,
              "slot1_key": slot1, "slot2_key": slot2,
              "h2h_choice": "The first set" if winner_slot == 1 else "The second set",
              "h2h_choice_slot": winner_slot, "h2h_choice_key": winner_key,
              "h2h_magnitude": "Clearly better",
              "h2h_why": "One was noticeably easier to follow than the other one was.",
              "standby": "Yes, no reservations", "total_ms": 1_500_000,
              "completion_code": "TESTCODE"})
    for s, k in (("1", slot1), ("2", slot2)):
        score = HIGH if keys[k]["version"] == "new" else LOW
        r["s%s_overall" % s] = score
        for f in ("visuals", "audio", "pacing"):
            r["s%s_%s" % (s, f)] = score
        r["s%s_errors" % s] = "No, nothing I noticed"
        r["s%s_speaker" % s] = "The speaker did well"
        r["s%s_codeword" % s] = keys[k].get("codeword", "")
        r["s%s_comment" % s] = "A perfectly adequate answer written to clear the length gate."
        r["s%s_duration_sec" % s] = 560
        r["s%s_watched_sec" % s] = 540
        r["s%s_watch_pct" % s] = 0.964
        r["s%s_max_rate" % s] = 1
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default="decode_key.json")
    a = ap.parse_args()

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    keys = json.load(open(a.key)).get("keys", {})

    # Pick any pair that has both sides recorded.
    by_pair = {}
    for k, v in keys.items():
        by_pair.setdefault(v.get("pair", "?"), {})[v["version"]] = k
    pair = next((p for p, d in sorted(by_pair.items()) if "old" in d and "new" in d), None)
    if not pair:
        sys.exit("no pair in %s has both an old and a new key" % a.key)
    old_k, new_k = by_pair[pair]["old"], by_pair[pair]["new"]
    print("  pair %s:  %s = old   %s = new" % (pair, old_k, new_k))

    # A saw the archive first; B saw the recreation first. Same opinion either way.
    rows = [build_row("ATTR-A", old_k, new_k, keys, new_k, 2, pair, "TEST"),
            build_row("ATTR-B", new_k, old_k, keys, new_k, 1, pair, "TEST")]

    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    try:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=HEADERS)
            w.writeheader()
            w.writerows(rows)
        out = subprocess.run([sys.executable, os.path.join(here, "analysis.py"), path,
                              "--key", a.key], capture_output=True, text=True).stdout
    finally:
        os.remove(path)

    # The archive was rated LOW and the recreation HIGH by both raters, so a correct
    # attribution must recover exactly that regardless of the order they saw them in.
    want = "overall   old %.2f   new %.2f   delta %+.2f" % (LOW, HIGH, HIGH - LOW)
    got = next((l.strip() for l in out.splitlines() if l.strip().startswith("overall ")), "")
    ok_scores = got == want

    votes = next((l.strip() for l in out.splitlines() if "new preferred in" in l), "")
    ok_votes = "2 of 2" in votes

    print("  expected: %s" % want)
    print("  actual:   %s" % (got or "(no overall line)"))
    print("  votes:    %s" % (votes or "(none)"))
    print()
    if ok_scores and ok_votes:
        print("  PASS - ratings and votes attribute to the right version in both orders")
        return 0
    print("  FAIL - attribution is order-dependent. Do not analyse real data until fixed.")
    print()
    print(out)
    return 1


if __name__ == "__main__":
    sys.exit(main())
