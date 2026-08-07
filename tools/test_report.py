#!/usr/bin/env python3
"""Does the results page attribute every number to the RIGHT version?

The page's whole job is to survive the alternating order. So this builds rows where the
truth is known and deliberately opposite in the two orders, renders the page, and reads
the numbers back out of the HTML.

  rater A saw the RECREATION first  and scored it 5, archive 1
  rater B saw the ARCHIVE   first  and scored it 1, recreation 5

If the page keys off position rather than version, one of these comes out backwards.
Also feeds it rows that must be EXCLUDED, so a broken row cannot quietly count.
"""
import csv, html, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

KEY = json.load(open(os.path.join(ROOT, "decode_key.json")))["keys"]
# A pair whose two keys we can address by version.
PAIR = "P1"
new_key = next(k for k, v in KEY.items() if v.get("pair") == PAIR and v["version"] == "new")
old_key = next(k for k, v in KEY.items() if v.get("pair") == PAIR and v["version"] == "old")
CW = {k: (KEY[k].get("codeword") or "") for k in (new_key, old_key)}

HEAD = ["row_id", "ts_server", "ts_client", "study_tag", "form_version", "is_selftest",
        "participant_id", "pair_id", "cc_code", "video_source", "slot1_key", "slot2_key",
        "h2h_choice", "h2h_choice_slot", "h2h_choice_key", "h2h_magnitude", "h2h_why",
        "standby", "s1_comment", "h2h_other", "assign_source", "total_ms", "extra_json"]
for s in (1, 2):
    for f in ("overall", "audio", "visuals", "clarity", "audio_why", "codeword", "watched_sec",
              "duration_sec", "watch_pct", "seek_fwd", "max_rate", "rate_ms", "video_count"):
        HEAD.append("s%d_%s" % (s, f))

DUR = 540


def row(pid, first_version, scores, **over):
    """scores = {'new': (overall,audio,visuals,clarity), 'old': (...)}, keyed by VERSION."""
    order = ([new_key, old_key] if first_version == "new" else [old_key, new_key])
    r = {h: "" for h in HEAD}
    r.update({"row_id": pid, "study_tag": "pilot-2026-07", "form_version": "1.7.0",
              "is_selftest": "no", "participant_id": pid, "pair_id": PAIR,
              "cc_code": "EMBR-CC-00051", "video_source": "youtube",
              "slot1_key": order[0], "slot2_key": order[1],
              "standby": "Yes, no reservations", "assign_source": "server",
              "total_ms": int(DUR * 2 * 1.05 * 1000)})
    for s, k in ((1, order[0]), (2, order[1])):
        ver = KEY[k]["version"]
        o, a, v, cl = scores[ver]
        r["s%d_overall" % s] = o; r["s%d_audio" % s] = a; r["s%d_visuals" % s] = v
        r["s%d_clarity" % s] = cl
        r["s%d_codeword" % s] = CW[k]
        r["s%d_duration_sec" % s] = DUR
        r["s%d_watched_sec" % s] = int(DUR * .95)
        r["s%d_watch_pct" % s] = 0.95
        r["s%d_max_rate" % s] = 1.0
        r["s%d_seek_fwd" % s] = 0
        r["s%d_video_count" % s] = 1
    # Head-to-head, expressed by VERSION and converted to the slot they saw it in.
    want = over.pop("prefers", "new")
    wk = new_key if want == "new" else old_key
    r["h2h_choice_key"] = wk
    r["h2h_choice_slot"] = 1 if order[0] == wk else 2
    r["h2h_choice"] = "The first video" if r["h2h_choice_slot"] == 1 else "The second video"
    r["h2h_magnitude"] = "Clearly better"
    r.update(over)
    return r


def card_for(doc, pid):
    """The slice of HTML belonging to one rater's card."""
    i = doc.find('<span class="pid">%s<' % pid)
    assert i > 0, "no card rendered for %s" % pid
    j = doc.find("</article>", i)
    return doc[i:j]


def scores_in(block, version):
    """Read the three numbers out of the RECREATION or ARCHIVE side of a card."""
    cls = "new" if version == "new" else "old"
    m = re.search(r'<div class="side %s">(.*?)</div>\s*</div>' % cls, block, re.S)
    if not m:
        m = re.search(r'<div class="side %s">(.*)' % cls, block, re.S)
    seg = m.group(1)
    nums = re.findall(r"<b>([^<]*)</b>\s*([a-z-]+)", seg)
    return {label: val.strip() for val, label in nums}


fails = []


def check(cond, label, detail=""):
    print(("  ok    " if cond else "  FAIL  ") + label + (("   [%s]" % detail) if detail and not cond else ""))
    if not cond:
        fails.append(label)


rows = [
    # Opposite orders, identical truth: recreation 5/5/5, archive 1/2/1.
    row("A_NEWFIRST", "new", {"new": (5, 5, 5, 5), "old": (1, 2, 1, 1)}, prefers="new"),
    row("B_OLDFIRST", "old", {"new": (5, 5, 5, 5), "old": (1, 2, 1, 1)}, prefers="new"),
    # A rater who genuinely preferred the archive, in each order.
    row("C_NEWFIRST_PREFERS_OLD", "new", {"new": (2, 2, 2, 2), "old": (4, 4, 4, 4)}, prefers="old"),
    row("D_OLDFIRST_PREFERS_OLD", "old", {"new": (2, 2, 2, 2), "old": (4, 4, 4, 4)}, prefers="old"),
    # Rows that MUST be excluded.
    # ONE wrong code word: kept and flagged. It shows for five seconds, once, so a single
    # miss is what a blink looks like, and binning an otherwise complete response over it
    # throws away the feedback the study is for.
    row("E_ONECODEWORD", "new", {"new": (5, 5, 5, 5), "old": (3, 3, 3, 3)}, s1_codeword="nonsense"),
    # BOTH wrong: excluded. Getting neither is what leaving the tab playing looks like,
    # and watch-time cannot catch that because the player really is playing.
    row("E_BOTHCODEWORDS", "new", {"new": (5, 5, 5, 5), "old": (3, 3, 3, 3)},
        s1_codeword="nonsense", s2_codeword="alsononsense"),
    row("F_LOWWATCH", "old", {"new": (5, 5, 5, 5), "old": (3, 3, 3, 3)}, s2_watch_pct=0.40),
    row("G_FASTPLAY", "new", {"new": (5, 5, 5, 5), "old": (3, 3, 3, 3)}, s1_max_rate=2.0),
    row("H_NOCHOICE", "new", {"new": (5, 5, 5, 5), "old": (3, 3, 3, 3)}),
    row("I_SELFTEST", "new", {"new": (5, 5, 5, 5), "old": (3, 3, 3, 3)}, is_selftest="yes"),
    row("J_WRONGTAG", "new", {"new": (5, 5, 5, 5), "old": (3, 3, 3, 3)}, study_tag="demo-2026-08"),
    row("K_SHORTSESSION", "new", {"new": (5, 5, 5, 5), "old": (3, 3, 3, 3)}, total_ms=60_000),
]
# By row_id, NOT by index. This was rows[7], which silently pointed at a different row
# the moment another fixture was inserted above it, blanking the wrong one's choice and
# leaving H_NOCHOICE with a choice it was supposed to be missing.
_h = next(x for x in rows if x["row_id"] == "H_NOCHOICE")
_h["h2h_choice_key"] = ""; _h["h2h_choice_slot"] = ""; _h["h2h_choice"] = ""

# One honest rater who submitted TWICE. The submit path retries, so a submission that
# reached the Sheet but whose response was lost produces a second identical row. The page
# counted every row as its own rater until 2026-08-07, which inflated both the headline and
# the means, while analysis.py had always dropped the extra - so the two disagreed on the
# same export. Both L rows carry the same participant_id.
dup_a = row("L_DOUBLESUBMIT", "new", {"new": (5, 5, 5, 5), "old": (3, 3, 3, 3)}, prefers="new")
dup_b = row("L_DOUBLESUBMIT", "new", {"new": (5, 5, 5, 5), "old": (3, 3, 3, 3)}, prefers="new")
dup_b["row_id"] = "L_DOUBLESUBMIT_RETRY"
rows += [dup_a, dup_b]

tmp = tempfile.mkdtemp()
csvp = os.path.join(tmp, "t.csv"); outp = os.path.join(tmp, "r.html")
with open(csvp, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=HEAD); w.writeheader(); w.writerows(rows)
res = subprocess.run([sys.executable, os.path.join(HERE, "make_report.py"), csvp,
                      "--out", outp], capture_output=True, text=True)
assert res.returncode == 0, res.stderr
doc = open(outp, encoding="utf-8").read()

print("=" * 74)
print("REPORT ATTRIBUTION TEST")
print("=" * 74)

# 1. Attribution survives the order swap.
for pid in ("A_NEWFIRST", "B_OLDFIRST"):
    blk = card_for(doc, pid)
    got_new = scores_in(blk, "new"); got_old = scores_in(blk, "old")
    check(got_new.get("overall") == "5" and got_new.get("narration") == "5",
          "%s: recreation's own scores land on the recreation" % pid, str(got_new))
    check(got_old.get("overall") == "1" and got_old.get("narration") == "2",
          "%s: archive's own scores land on the archive" % pid, str(got_old))

# 2. The two orders must produce IDENTICAL version-keyed output.
a, b = card_for(doc, "A_NEWFIRST"), card_for(doc, "B_OLDFIRST")
check(scores_in(a, "new") == scores_in(b, "new") and scores_in(a, "old") == scores_in(b, "old"),
      "same truth in both orders reads the same on the page")

# 3. The page must say which position they actually watched it in.
check("they saw this <strong>first</strong>" in a.split('class="side old"')[0],
      "A_NEWFIRST: recreation is marked as watched first")
check("they saw this <strong>second</strong>" in b.split('class="side old"')[0],
      "B_OLDFIRST: recreation is marked as watched second")

# 4. Who they picked, by version not position.
check("picked RECREATION" in a and "picked RECREATION" in b, "preference decoded in both orders")
for pid in ("C_NEWFIRST_PREFERS_OLD", "D_OLDFIRST_PREFERS_OLD"):
    check("picked ARCHIVE" in card_for(doc, pid), "%s: archive preference not flipped" % pid)

# 5. Ratings-vs-pick agreement flag.
check("ratings agree with the pick" in a, "A: agreement flag set when they line up")
check("ratings agree with the pick" in card_for(doc, "C_NEWFIRST_PREFERS_OLD"),
      "C: agreement flag set for an archive-preferring rater too")

# 6. Bad rows excluded, and each one SAID so rather than silently dropped.
for pid, why in (("E_BOTHCODEWORDS", "code word"), ("F_LOWWATCH", "watched"),
                 ("G_FASTPLAY", "x"), ("K_SHORTSESSION", "session")):
    blk = card_for(doc, pid)
    check("<strong>Excluded:</strong>" in blk, "%s marked excluded on its card" % pid)
    check(why.lower() in blk.lower(), "%s: reason mentions %r" % (pid, why))
check("Excluded:" in card_for(doc, "H_NOCHOICE") or "NOT RECORDED" in card_for(doc, "H_NOCHOICE"),
      "H_NOCHOICE: a missing head-to-head is visible, not treated as a vote")
check("I_SELFTEST" not in doc.split('<h2>Not counted</h2>')[0].split('<h2>Every rater</h2>')[1]
      if '<h2>Every rater</h2>' in doc else True,
      "selftest row does not appear as a rater")
check("selftest" in doc, "selftest row listed under Not counted")
check("study tag" in doc and "demo-2026-08" in doc, "wrong-study-tag row listed with its tag")

# 6a. ONE wrong code word is kept, and says so on the card.
one = card_for(doc, "E_ONECODEWORD")
check("<strong>Excluded:</strong>" not in one, "a single missed code word is NOT excluded")
check("Counted, with a note" in one, "the single miss is noted on the card")

# 6b. A rater who submitted twice counts ONCE.
dup_cards = doc.count('<span class="pid">L_DOUBLESUBMIT<')
check(dup_cards == 1, "a double submission produces ONE card, not two",
      "found %d" % dup_cards)
check("duplicate participant" in doc, "the extra submission is listed as a duplicate")

# 7. The headline counts CLEAN rows only: 5 clean (A,B,C,D + one L), 3 preferring new.
m = re.search(r'<span class="big">(\d+) of (\d+)</span>', doc)
check(bool(m), "headline present")
if m:
    check(m.group(2) == "6", "headline denominator counts only clean rows, deduped",
          "got %s" % m.group(2))
    check(m.group(1) == "4", "headline numerator counts recreation wins", "got %s" % m.group(1))

# 8. Mean table uses version, not position: recreation overall (5+5+2+2)/4 = 3.50,
#    archive (1+1+4+4)/4 = 2.50.
mt = re.search(r"<tr><td>Overall</td><td>([\d.]+)</td><td>([\d.]+)</td>", doc)
check(bool(mt), "mean table rendered")
if mt:
    check(mt.group(1) == "2.67" and mt.group(2) == "4.00",
          "mean table: archive 2.67, recreation 4.00", "got %s / %s" % mt.groups())

# 9. Nothing in the page leaks a rater-facing hint of which is which... it SHOULD say,
#    this file is internal. Instead assert it warns about that plainly.
check("Do not share it outside the team" in doc, "page warns it contains the blind")

print()
if fails:
    print("%d FAILED: %s" % (len(fails), "; ".join(fails)))
    sys.exit(1)
print("PASS - the page decodes by version, survives both orders, and excludes bad rows")
