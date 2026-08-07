#!/usr/bin/env python3
"""
Read one response at a time, in plain English, with the blind decoded.

    python3 tools/decode_responses.py responses.csv --key decode_key.json
    python3 tools/decode_responses.py responses.csv --only-problems

analysis.py answers "did the pipeline win". This answers "what did THIS person
actually see, and does their row hang together" - which is what you need when
deciding whether to approve or reject someone on CloudResearch, and when someone
asks how you know a rating belongs to the video you think it does.

For every response it resolves:
  - which course, and which build of it played in each position
  - whether the code word they typed matches the one burned into THAT set's
    second video, which is the check that they were still watching near the end
  - how much of each set they genuinely watched, and whether they tried to skip
  - their ratings, attributed to old or new rather than to slot 1 or slot 2
  - which set they preferred, decoded, and how big they said the gap was
  - every quality gate, and which ones this row fails

Standard library only.
"""

import argparse, csv, json, sys

OK, BAD, MEH = "ok", "FAIL", "--"


def load_key(path):
    raw = json.load(open(path))
    return raw.get("keys", raw)


def field(row, name):
    """Read a field whether it has its own column or arrived in extra_json."""
    v = row.get(name)
    if v not in (None, ""):
        return v
    raw = row.get("extra_json") or ""
    if not raw:
        return ""
    try:
        return json.loads(raw).get(name, "") or ""
    except (ValueError, AttributeError):
        return ""


def num(x, d=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--key", default="decode_key.json")
    ap.add_argument("--only-problems", action="store_true",
                    help="print only rows that fail a gate - the reject shortlist")
    a = ap.parse_args()

    KEY = load_key(a.key)
    rows = list(csv.DictReader(open(a.csv, newline="", encoding="utf-8-sig")))
    shown = 0

    for r in rows:
        problems = []
        pid = (r.get("participant_id") or "?").strip()
        pair = r.get("pair_id") or "?"
        cc = r.get("cc_code") or "?"

        lines = []
        lines.append("participant %s   pair %s   course %s   form %s"
                     % (pid, pair, cc, r.get("form_version", "?")))
        tag = (r.get("study_tag") or "").strip()
        if (r.get("is_selftest") or "").lower() == "yes":
            problems.append("marked as a self-test")
        lines.append("study tag %s%s" % (tag, "   (self-test)" if
                     (r.get("is_selftest") or "").lower() == "yes" else ""))

        for s in ("1", "2"):
            k = r.get("slot%s_key" % s, "")
            info = KEY.get(k)
            if not info:
                problems.append("slot %s key %r is not in the decode key" % (s, k))
                lines.append("  position %s: UNKNOWN key %r" % (s, k))
                continue
            side = info["version"]
            label = "the recreation" if side == "new" else "the archived version"

            watched = num(r.get("s%s_watched_sec" % s), 0) or 0
            dur = num(r.get("s%s_duration_sec" % s), 0) or 0
            pct = (watched / dur * 100) if dur else 0
            nvid = field(r, "s%s_video_count" % s) or "?"

            want = (info.get("codeword") or "").strip().lower()
            got = (r.get("s%s_codeword" % s) or "").strip().lower()
            if not want:
                cw = "no code word set for this clip"
            elif got == want:
                cw = "'%s' correct" % got
            else:
                cw = "'%s' WRONG, expected '%s'" % (got or "(blank)", want)
                problems.append("wrong code word on position %s" % s)

            if pct < 85:
                problems.append("only %.0f%% watched on position %s" % (pct, s))
            rate = num(r.get("s%s_max_rate" % s), 1) or 1
            if rate > 1.25:
                problems.append("played position %s at %.1fx" % (s, rate))
            # NOTE: there is deliberately no per-video comment printed here. The form
            # has exactly one free-text catch-all, `s1_comment`, and despite the name it
            # lives in the END block, not in section 1. Printing it under position 1
            # labelled it as feedback about that video, which it is not, and printed
            # "(skipped the optional comment)" under position 2 for everyone, because
            # s2_comment does not exist at all. It is now shown once, at the end, where
            # the rater actually wrote it. The only genuinely per-video free text is
            # audio_why, printed below.
            lines.append("  position %s  =  %-18s  key %s%s"
                         % (s, label, k,
                            "   %s videos" % nvid if str(nvid) not in ("1", "?") else ""))
            lines.append("      watched %.0f%% of %.0fs   seeks fwd %s   max speed %.2fx"
                         % (pct, dur, r.get("s%s_seek_fwd" % s, "?"), rate))
            lines.append("      code word: %s" % cw)
            lines.append("      overall %s  voice %s  on-screen %s"
                         % (field(r, "s%s_overall" % s) or "-", field(r, "s%s_audio" % s) or "-",
                            field(r, "s%s_visuals" % s) or "-"))
            nw = field(r, "s%s_audio_why" % s)
            if nw:
                lines.append("      on the narration: \"%s\"" % str(nw)[:80])


        wk = r.get("h2h_choice_key", "")
        winfo = KEY.get(wk)
        if not winfo:
            problems.append("head-to-head choice %r is not in the decode key" % wk)
            verdict = "UNKNOWN"
        else:
            verdict = "%s (%s)" % ("the recreation" if winfo["version"] == "new"
                                   else "the archived version", wk)
        mag = field(r, "h2h_magnitude") or "-"
        why = (r.get("h2h_why") or "").strip()
        lines.append("  preferred: %s   position %s   margin: %s"
                     % (verdict, r.get("h2h_choice_slot", "?"), mag))
        lines.append("      %s" % ('"%s"' % (why[:96] + ("..." if len(why) > 96 else ""))
                                    if why else "(no explanation given - optional)"))
        # Not a reject reason: h2h_why is optional and only shown to raters who
        # reported a clear difference. Printed so it can be read, never gated.
        sb = field(r, "standby")
        if sb:
            lines.append("  would train a coworker with their pick: %s" % sb)

        tot = num(r.get("total_ms"), 0) or 0
        clips = sum((num(r.get("s%s_duration_sec" % s), 0) or 0) for s in ("1", "2"))
        floor = max(480, 0.85 * clips) if clips else 480
        if tot and tot / 1000 < floor:
            problems.append("session only %ds, needs %ds for %ds of video"
                            % (tot / 1000, floor, clips))
        gen = (r.get("s1_comment") or "").strip()
        if gen:
            lines.append("  anything else (about the study as a whole, not one video):")
            lines.append("      \"%s\"" % (gen[:200] + ("..." if len(gen) > 200 else "")))
        oth = (r.get("h2h_other") or "").strip()
        if oth:
            lines.append("  other comments: \"%s\"" % (oth[:200] + ("..." if len(oth) > 200 else "")))
        lines.append("  session %.0f min   assignment: %s"
                     % (tot / 60000, r.get("assign_source", "?") or "?"))

        if a.only_problems and not problems:
            continue
        shown += 1
        print("=" * 78)
        print("\n".join(lines))
        if problems:
            print("  EXCLUDE - %s" % "; ".join(problems))
        else:
            print("  clean - passes every gate")
        print()

    print("=" * 78)
    print("%d of %d responses shown%s" % (shown, len(rows),
          " (problems only)" if a.only_problems else ""))
    print("Reject on the gates above, never on someone's rating. A rater who preferred")
    print("the archived version is data, not a bad participant.")


if __name__ == "__main__":
    main()
