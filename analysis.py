#!/usr/bin/env python3
"""
Embrace CloudResearch pilot - analysis.

Reads the CSV export of the "responses" sheet plus the private decode key, applies
the quality gates, and prints PASS/FAIL against the pre-registered criterion
locked 2026-07-30:

    The new pipeline is validated if raters prefer the new version in the blind
    head-to-head in at least 4 of 5 pairs, AND pooled preference for new is
    >= 65% (exact binomial p < .05 vs 50%), AND new's mean "overall" score
    exceeds old's by >= 0.5 on the 1-5 scale.

Standard library only - no pip install, no version drift.

    python3 analysis.py responses.csv --key decode_key.json
    python3 analysis.py responses.csv --key decode_key.json --include-excluded
"""

import argparse, csv, json, statistics as st, sys
from collections import defaultdict
from math import comb

# ---- pre-registered thresholds (do not edit after launch) -------------------
MIN_PAIRS_WON     = 4
MIN_POOLED_PREF   = 0.65
MAX_P             = 0.05
MIN_OVERALL_DELTA = 0.50
# ---- quality gates ---------------------------------------------------------
MIN_WATCH_PCT     = 0.85   # a hair under the 0.90 form gate, for timer slop
MIN_SESSION_SEC   = 480    # absolute floor, used only when durations didn't record
MIN_SESSION_FRAC  = 0.85   # of (video 1 + video 2) - the real floor, see below
MIN_COMMENT_CHARS = 40
MAX_PLAYBACK_RATE = 1.25   # video seconds per real second; >1 means sped-up playback

# The session floor is derived from the clips the rater was actually served rather
# than fixed. A flat 480 s was set when each side was assumed to be ~10 minutes;
# the clips measure ~9 minutes a side, so 480 s is under a third of a real session
# and would pass someone who cannot have watched. s1_duration_sec and
# s2_duration_sec ride along in every row, so the floor can track the actual
# video: a session shorter than MIN_SESSION_FRAC of the two clips combined could
# not have played them both. The flat floor remains as a backstop for rows where
# duration failed to record.

AI_FLAG = {"Probably computer-generated", "Definitely computer-generated"}


def exact_binom_p(k, n, sided="two"):
    """Exact binomial test against p=0.5."""
    if n == 0:
        return 1.0
    probs = [comb(n, i) / 2 ** n for i in range(n + 1)]
    if sided == "one":
        return sum(probs[k:])
    return sum(p for p in probs if p <= probs[k] + 1e-12)


def load_key(path):
    raw = json.load(open(path))
    keys = raw.get("keys", raw)
    out = {}
    for k, v in keys.items():
        if isinstance(v, str):
            v = {"version": v}
        ver = str(v.get("version", "")).strip().lower()
        if ver not in ("old", "new"):
            sys.exit("decode_key: key %r must be 'old' or 'new', got %r" % (k, ver))
        out[k] = {"version": ver, "pair": v.get("pair", ""), "codeword": v.get("codeword", "")}
    return out


def num(x, default=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--key", default="decode_key.json")
    ap.add_argument("--include-excluded", action="store_true",
                    help="report on all rows, ignoring quality gates (sensitivity check)")
    a = ap.parse_args()

    KEY = load_key(a.key)
    rows = list(csv.DictReader(open(a.csv, newline="", encoding="utf-8-sig")))

    kept, dropped, seen_pid = [], [], set()
    for r in rows:
        why = []
        if (r.get("is_selftest") or "").lower() == "yes":
            why.append("selftest")
        pid = (r.get("participant_id") or "").strip()
        if not pid:
            why.append("no participant id")
        elif pid in seen_pid:
            why.append("duplicate participant")
        seen_pid.add(pid)

        for s in ("1", "2"):
            wp = num(r.get("s%s_watch_pct" % s), 0) or 0
            if wp < MIN_WATCH_PCT:
                why.append("watch %d%% on video %s" % (int(wp * 100), s))
            k = r.get("slot%s_key" % s, "")
            expect = KEY.get(k, {}).get("codeword", "")
            got = (r.get("s%s_codeword" % s) or "").strip().lower()
            if expect and got != expect.strip().lower():
                why.append("code word wrong on video %s" % s)
            if len((r.get("s%s_comment" % s) or "").strip()) < MIN_COMMENT_CHARS:
                why.append("thin comment on video %s" % s)
            rate = num(r.get("s%s_max_rate" % s), 1) or 1
            if rate > MAX_PLAYBACK_RATE:
                why.append("played video %s at %.1fx" % (s, rate))

        tot = num(r.get("total_ms"), 0) or 0
        clips = sum((num(r.get("s%s_duration_sec" % s), 0) or 0) for s in ("1", "2"))
        floor = max(MIN_SESSION_SEC, MIN_SESSION_FRAC * clips) if clips else MIN_SESSION_SEC
        if tot and tot / 1000 < floor:
            why.append("session only %ds, needs %ds for %ds of video"
                       % (int(tot / 1000), int(floor), int(clips)))
        if not r.get("h2h_choice_key"):
            why.append("no head-to-head choice")

        (dropped if why else kept).append((r, why))

    use = [r for r, _ in (kept + dropped)] if a.include_excluded else [r for r, _ in kept]

    print("=" * 74)
    print("EMBRACE CLOUDRESEARCH PILOT - ANALYSIS")
    print("=" * 74)
    print("rows in export      %d" % len(rows))
    print("passed quality gate %d" % len(kept))
    print("excluded            %d" % len(dropped))
    for r, why in dropped:
        print("   - %-22s %-16s %s" % (r.get("row_id", "?"),
                                       (r.get("participant_id") or "?")[:14],
                                       "; ".join(why)))
    if a.include_excluded:
        print("\n!! --include-excluded is ON: excluded rows are being analysed too.")
    if not use:
        sys.exit("\nNo usable rows.")

    # ---------- reshape into per-rater old/new records ----------
    recs = []
    for r in use:
        rec = {"pid": r.get("participant_id"), "pair": r.get("pair_id"), "row": r.get("row_id")}
        ok = True
        for s in ("1", "2"):
            k = r.get("slot%s_key" % s, "")
            if k not in KEY:
                print("   ! unknown version key %r on row %s - skipped" % (k, r.get("row_id")))
                ok = False
                break
            side = KEY[k]["version"]
            for field in ("overall", "visuals", "audio", "pacing", "standby"):
                rec["%s_%s" % (side, field)] = num(r.get("s%s_%s" % (s, field)))
            rec["%s_ai" % side] = r.get("s%s_ai_read" % s, "") in AI_FLAG
            rec["%s_err" % side] = (r.get("s%s_errors" % s) or "").startswith("Yes")
            rec["%s_slot" % side] = int(s)
        if not ok:
            continue
        win_key = r.get("h2h_choice_key", "")
        if win_key not in KEY:
            continue
        rec["winner"] = KEY[win_key]["version"]
        rec["winner_slot"] = int(r.get("h2h_choice_slot") or 0)
        rec["confidence"] = num(r.get("h2h_confidence"))
        recs.append(rec)

    n = len(recs)
    if not n:
        sys.exit("\nNo rows survived decoding - check decode_key.json against slot1_key/slot2_key.")
    wins_new = sum(1 for x in recs if x["winner"] == "new")
    pref = wins_new / n
    p2 = exact_binom_p(wins_new, n, "two")
    p1 = exact_binom_p(wins_new, n, "one")

    print("\n" + "-" * 74)
    print("CLAUSE 1 - head-to-head by pair (need new ahead in >= 4 of 5)")
    print("-" * 74)
    by_pair = defaultdict(lambda: [0, 0])
    for x in recs:
        by_pair[x["pair"]][0 if x["winner"] == "new" else 1] += 1
    pairs_won = 0
    for pid in sorted(by_pair):
        nw, ow = by_pair[pid]
        won = nw > ow
        pairs_won += won
        verdict = "new ahead" if won else ("tie" if nw == ow else "OLD ahead")
        print("  %-5s new %2d : %-2d old   %s" % (pid, nw, ow, verdict))
    print("\n  pairs where new leads: %d of %d" % (pairs_won, len(by_pair)))

    print("\n" + "-" * 74)
    print("CLAUSE 2 - pooled preference (need >= 65%% AND exact binomial p < .05)")
    print("-" * 74)
    print("  new preferred in %d of %d paired votes = %.1f%%" % (wins_new, n, pref * 100))
    print("  exact binomial vs 50%%:  two-sided p = %.4f   one-sided p = %.4f" % (p2, p1))
    need = next((k for k in range(n + 1)
                 if k / n >= MIN_POOLED_PREF and exact_binom_p(k, n, "two") < MAX_P), None)
    print("  the locked criterion reads two-sided; at n=%d both clauses hold from %s wins up"
          % (n, need))

    print("\n" + "-" * 74)
    print("CLAUSE 3 - mean 'overall' score (need new - old >= 0.50)")
    print("-" * 74)

    def m(f):
        v = [x[f] for x in recs if x.get(f) is not None]
        return st.mean(v) if v else float("nan")

    for field in ("overall", "visuals", "audio", "pacing", "standby"):
        o, nw = m("old_%s" % field), m("new_%s" % field)
        print("  %-9s old %.2f   new %.2f   delta %+.2f" % (field, o, nw, nw - o))
    diffs = [x["new_overall"] - x["old_overall"] for x in recs
             if x.get("new_overall") is not None and x.get("old_overall") is not None]
    delta = st.mean(diffs) if diffs else float("nan")
    sd = st.stdev(diffs) if len(diffs) > 1 else 0.0
    print("\n  within-rater overall delta: mean %+.2f  sd %.2f  n %d" % (delta, sd, len(diffs)))
    print("  within-rater is the number that matters - each rater is their own control")

    print("\n" + "-" * 74)
    print("DIAGNOSTICS (context, not part of the criterion)")
    print("-" * 74)
    slot1_wins = sum(1 for x in recs if x["winner_slot"] == 1)
    print("  position effect     first-shown video won %d of %d (%.0f%%) - near 50%% means"
          " order is not driving the result" % (slot1_wins, n, slot1_wins / n * 100))
    for side in ("old", "new"):
        ai = sum(1 for x in recs if x.get("%s_ai" % side))
        er = sum(1 for x in recs if x.get("%s_err" % side))
        print("  %-3s reads-as-AI %d/%d (%.0f%%)   noticed errors %d/%d (%.0f%%)"
              % (side, ai, n, ai / n * 100, er, n, er / n * 100))
    conf = [x["confidence"] for x in recs if x.get("confidence") is not None]
    if conf:
        print("  mean confidence in the head-to-head choice: %.2f / 5" % st.mean(conf))
    agree = [max(v) / sum(v) for v in by_pair.values() if sum(v)]
    if agree:
        print("  mean within-pair rater agreement: %.0f%% (50%% = coin flip, 100%% = unanimous)"
              % (st.mean(agree) * 100))

    c1 = pairs_won >= MIN_PAIRS_WON
    c2 = pref >= MIN_POOLED_PREF and p2 < MAX_P
    c3 = delta >= MIN_OVERALL_DELTA
    print("\n" + "=" * 74)
    print("PRE-REGISTERED CRITERION")
    print("=" * 74)
    print("  [%s]  new ahead in >= %d of 5 pairs        (%d of %d)"
          % ("PASS" if c1 else "FAIL", MIN_PAIRS_WON, pairs_won, len(by_pair)))
    print("  [%s]  pooled pref >= 65%% and p < .05      (%.1f%%, p = %.4f)"
          % ("PASS" if c2 else "FAIL", pref * 100, p2))
    print("  [%s]  overall delta >= +0.50              (%+.2f)"
          % ("PASS" if c3 else "FAIL", delta))
    print("-" * 74)
    print("  VERDICT: %s - all three clauses must hold"
          % ("VALIDATED" if (c1 and c2 and c3) else "NOT VALIDATED"))
    print("=" * 74)


if __name__ == "__main__":
    main()
