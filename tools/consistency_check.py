#!/usr/bin/env python3
"""
Do the form, the analysis and the test generator still agree?

    python3 tools/consistency_check.py

The form writes strings; the analysis compares against strings; the generator invents
strings. Nothing binds them together, so a reworded option silently breaks a
diagnostic - the analysis reports 0% rather than erroring, which is the worst kind of
failure because it looks like a finding. This has already happened twice: once when
the AI question was reworded, once when "The first set" became "The first video".

Exits non-zero on any drift. Run before launch and before analysing real data.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
form = open(os.path.join(HERE, "index.html")).read()
an   = open(os.path.join(HERE, "analysis.py")).read()
gen  = open(os.path.join(HERE, "tools", "make_fake_responses.py")).read()

problems, checks = [], []


def note(ok, label, detail=""):
    checks.append((ok, label, detail))
    if not ok:
        problems.append(label + ("  " + detail if detail else ""))


def form_opts(qid):
    """The option strings the form offers for a choice question."""
    m = re.search(r'\{\s*id:"%s".*?opts:\[(.*?)\]' % re.escape(qid), form, re.S)
    return [s.strip().strip('"') for s in m.group(1).split(",")] if m else None


def form_ids():
    return re.findall(r'\{\s*id:"([a-z0-9_]+)"', form)


# --- the head-to-head choice strings, which payload() tests against literally ------
opts = form_opts("h2h_choice")
note(opts == ["The first video", "The second video"],
     "h2h_choice options", str(opts))
m = re.search(r'D\.h2h_choice_slot = D\.h2h_choice === "([^"]+)"', form)
note(m and opts and m.group(1) == opts[0],
     "payload() slot test matches the first option",
     "tests %r, option is %r" % (m.group(1) if m else None, opts[0] if opts else None))
note(gen.count('"The first video"') >= 1 and gen.count('"The second video"') >= 1,
     "generator uses the same choice strings")

# --- magnitude, which gates the conditional why-box and the sensitivity check ------
mag = form_opts("h2h_magnitude")
note(mag == ["Barely any difference", "Slightly better", "Clearly better", "Much better"],
     "h2h_magnitude options", str(mag))
show = re.search(r'\{\s*id:"h2h_why".*?showIf:\{\s*id:"h2h_magnitude",\s*vals:\[(.*?)\]',
                 form, re.S)
shown_for = [s.strip().strip('"') for s in show.group(1).split(",")] if show else None
note(shown_for == ["Clearly better", "Much better"],
     "why-box appears only for a clear preference", str(shown_for))
note(all(v in (mag or []) for v in (shown_for or ["x"])),
     "those values exist in the magnitude options")
note('"Barely any difference"' in an,
     "analysis.py knows the sensitivity-check value")

# --- the four rating dimensions ---------------------------------------------------
am = re.search(r'METRICS = \((.*?)\)', an, re.S)
metrics = [s.strip().strip('"') for s in am.group(1).split(",") if s.strip()] if am else []
ids = form_ids()
note(sorted(metrics) == sorted(["overall", "audio", "visuals", "clarity"]),
     "analysis METRICS", str(metrics))
for mt in metrics:
    note(mt in ids, "form asks for metric %r" % mt)
    note(('"%s"' % mt) in gen or ("'%s'" % mt) in gen or mt in gen,
         "generator emits metric %r" % mt)

# --- questions removed from the form must not be referenced anywhere --------------
for dead in ("speaker", "speaker_issues", "speaker_distract", "errors", "pacing", "ai_read"):
    note(dead not in ids, "removed question %r is gone from the form" % dead)
    note(("s%%s_%s" % dead) not in an and ('"%s"' % dead) not in an,
         "analysis.py no longer reads %r" % dead)

# --- the narration probe, which is now the only route to reads-as-artificial ------
note("audio_why" in ids, "narration probe exists in the form")
note("audio_why" in an, "analysis.py reads the narration probe")
note("audio_why" in gen, "generator emits the narration probe")
note("LOW_NARRATION" in an, "analysis.py defines the low-narration threshold")

# --- code word: outside the locked card, and never present in any public file -----
note('id="cw${slot}"' in form, "code word input is rendered under the video")
note('D["s" + slot + "_codeword"] = cw.value.trim()' in form,
     "code word is collected in the continue handler")
words = []
kp = os.path.join(HERE, "decode_key.json")
if os.path.exists(kp):
    words = [v.get("codeword", "") for v in json.load(open(kp))["keys"].values() if v.get("codeword")]
leaked = [w for w in words if w and w in form]
note(not leaked, "no code word appears in index.html", str(leaked))
for pub in ("config.js", "demo/config.js", "apps_script/Code.gs", "decode_key.example.json"):
    txt = open(os.path.join(HERE, pub)).read()
    bad = [w for w in words if w and w in txt]
    note(not bad, "no code word appears in %s" % pub, str(bad))

# --- resume ------------------------------------------------------------------------
note("saveArmed" in form, "resume: saving is armed only after resume reads")
note("snapshotLive" in form, "resume: live answers are snapshotted")
note("priorMs + (Date.now() - t0)" in form, "resume: elapsed time carries across")

print("=" * 74)
print("CONSISTENCY CHECK")
print("=" * 74)
for ok, label, detail in checks:
    print("  %s  %s%s" % ("ok  " if ok else "FAIL", label,
                          ("   [%s]" % detail) if detail and not ok else ""))
print()
if problems:
    print("%d problem(s). The form and the analysis disagree - fix before launch." % len(problems))
    sys.exit(1)
print("All %d checks pass. The form, the analysis and the generator agree." % len(checks))
