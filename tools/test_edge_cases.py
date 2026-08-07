#!/usr/bin/env python3
"""EDGE CASES for the three readers: analysis.py, make_report.py, decode_responses.py.

Feeds each of them the malformed, empty and hostile inputs a real run can produce and
fails only on an unhandled exception. A guarded non-zero exit with a readable message
("No usable rows") is correct behaviour and passes here.

Covers: no rows, one row, every row excluded, unknown keys, a blank head-to-head choice,
zero durations, non-numeric ratings, emoji and accents, a 2000-character comment, HTML
and spreadsheet-formula injection in free text, duplicate participant ids, and watch_pct
arriving as 95 rather than 0.95.

    python3 tools/test_edge_cases.py
"""
import csv, json, os, subprocess, sys, tempfile
ROOT=os.path.expanduser("~/cloudresearch_pilot")
KEY=json.load(open(os.path.join(ROOT,"decode_key.json")))["keys"]
P="P1"
nk=next(k for k,v in KEY.items() if v.get("pair")==P and v["version"]=="new")
ok=next(k for k,v in KEY.items() if v.get("pair")==P and v["version"]=="old")
CW={k:(KEY[k].get("codeword") or "") for k in (nk,ok)}
HEAD=["row_id","ts_server","ts_client","study_tag","form_version","is_selftest","participant_id",
 "pair_id","cc_code","video_source","slot1_key","slot2_key","h2h_choice","h2h_choice_slot",
 "h2h_choice_key","h2h_magnitude","h2h_why","standby","s1_comment","h2h_other","assign_source",
 "total_ms","extra_json"]
for s in (1,2):
    for f in ("overall","audio","visuals","clarity","audio_why","codeword","watched_sec",
              "duration_sec","watch_pct","seek_fwd","max_rate","rate_ms","video_count"):
        HEAD.append("s%d_%s"%(s,f))
D=540
def row(pid,**over):
    r={h:"" for h in HEAD}
    r.update({"row_id":pid,"study_tag":"pilot-2026-07","form_version":"1.8.0","is_selftest":"no",
      "participant_id":pid,"pair_id":P,"cc_code":"EMBR-CC-00051","video_source":"youtube",
      "slot1_key":nk,"slot2_key":ok,"standby":"Yes, no reservations","assign_source":"server",
      "total_ms":int(D*2*1.05*1000),"h2h_choice_key":nk,"h2h_choice_slot":1,
      "h2h_choice":"The first video","h2h_magnitude":"Clearly better"})
    for s,k in ((1,nk),(2,ok)):
        for f,v in (("overall",4),("audio",4),("visuals",4),("clarity",4)):
            r["s%d_%s"%(s,f)]=v
        r["s%d_codeword"%s]=CW[k]; r["s%d_duration_sec"%s]=D
        r["s%d_watched_sec"%s]=int(D*.95); r["s%d_watch_pct"%s]=0.95
        r["s%d_max_rate"%s]=1.0; r["s%d_seek_fwd"%s]=0; r["s%d_video_count"%s]=1
    r.update(over); return r

def run(name, rows, expect_crash=False):
    d=tempfile.mkdtemp(); c=os.path.join(d,"t.csv"); o=os.path.join(d,"r.html")
    with open(c,"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=HEAD); w.writeheader(); w.writerows(rows)
    res_a=subprocess.run([sys.executable,os.path.join(ROOT,"analysis.py"),c,"--key",
                          os.path.join(ROOT,"decode_key.json")],capture_output=True,text=True)
    res_r=subprocess.run([sys.executable,os.path.join(ROOT,"tools/make_report.py"),c,"--out",o],
                          capture_output=True,text=True)
    res_d=subprocess.run([sys.executable,os.path.join(ROOT,"tools/decode_responses.py"),c],
                          capture_output=True,text=True)
    bad=[]
    for label,res in (("analysis.py",res_a),("make_report.py",res_r),("decode_responses.py",res_d)):
        out=(res.stderr or "")+(res.stdout or "")
        # A non-zero exit carrying a plain explanation is CORRECT: there is nothing to
        # analyse, and saying so beats printing an empty table. Only an unhandled
        # exception counts as a failure, so judge on tracebacks rather than exit codes.
        if "Traceback (most recent call last)" in out:
            last=[l for l in out.strip().splitlines() if l.strip()][-1]
            bad.append("%s raised %s"%(label,last[:70]))
    status="CRASH" if bad else "ok"
    print("  %-6s %-44s %s"%(status,name,"; ".join(bad)[:110]))
    return not bad

results=[]
results.append(run("no rows at all", []))
results.append(run("one clean row", [row("ONE")]))
results.append(run("every row excluded (all selftest)", [row("S1",is_selftest="yes"),row("S2",is_selftest="yes")]))
results.append(run("every row wrong study tag", [row("T1",study_tag="other-study")]))
results.append(run("all rows fail the watch gate", [row("W1",s1_watch_pct=0.1),row("W2",s2_watch_pct=0.2)]))
results.append(run("unknown key in slot1", [row("K1",slot1_key="zzzz")]))
results.append(run("blank h2h choice", [row("NC",h2h_choice_key="",h2h_choice_slot="",h2h_choice="")]))
results.append(run("blank magnitude and why", [row("BM",h2h_magnitude="",h2h_why="")]))
results.append(run("zero duration on both clips", [row("Z0",s1_duration_sec=0,s2_duration_sec=0)]))
results.append(run("missing total_ms", [row("NT",total_ms="")]))
results.append(run("non-numeric ratings", [row("NN",s1_overall="four",s2_overall="n/a")]))
# Built from escapes rather than literals. A rater may well type an em dash and it must
# round-trip, but a literal one in this file would trip the repo-wide no-em-dash check.
DASH = "\u2014"
results.append(run("emoji, accents and an em dash in free text",
    [row("UNI", s1_comment="Tr\u00e9s bien \U0001f600 the narrator\u2019s tone " + DASH + " clear",
         h2h_why="\u00fcn\u00efc\u00f6d\u00e9 \u2705 test")]))
results.append(run("2000-char comment", [row("LONG",s1_comment="x"*2000,h2h_why="y"*2000)]))
results.append(run("html injection in free text",
    [row("XSS",s1_comment="<script>alert(1)</script>",h2h_why="<img src=x onerror=alert(1)>")]))
results.append(run("csv injection formula in free text", [row("FRM",s1_comment="=SUM(A1:A9)")]))
results.append(run("duplicate participant id", [row("DUP"),row("DUP")]))
results.append(run("watch_pct given as 95 not 0.95", [row("PCT",s1_watch_pct=95,s2_watch_pct=96)]))
print()
print("%d of %d edge cases handled without crashing"%(sum(results),len(results)))
sys.exit(0 if all(results) else 1)
