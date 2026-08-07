#!/usr/bin/env python3
"""Turn a responses CSV into ONE readable page.

Why this exists: the two videos are shown in alternating order, so "position 1" is the
recreation for about half the raters and the archive for the other half. Reading a raw
CSV, or even the text decoder, it is easy to attribute a comment to the wrong version.
This page never shows a position without saying which VERSION sat there, colours the two
consistently throughout, and puts the recreation's numbers in the same column on every
card regardless of the order that rater actually saw.

Contains the blind (which key is old and which is new), so it is written locally and is
gitignored. Never publish it.

    python3 tools/make_report.py responses.csv [--key decode_key.json] [--out report.html]
"""
import argparse, csv, html, json, os, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def field(row, name):
    """Read a column, falling back to the extra_json overflow the Apps Script writes."""
    if row.get(name) not in (None, ""):
        return row[name]
    raw = row.get("extra_json") or ""
    if raw:
        try:
            return json.loads(raw).get(name, "")
        except Exception:
            return ""
    return ""


def num(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def esc(v):
    return html.escape(str(v or ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--key", default=os.path.join(ROOT, "decode_key.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "report.html"))
    ap.add_argument("--study-tag", default="pilot-2026-07")
    a = ap.parse_args()

    KEY = json.load(open(a.key))["keys"]
    rows = list(csv.DictReader(open(a.csv)))

    cards, kept, dropped = [], [], []
    for r in rows:
        tag = (r.get("study_tag") or "").strip()
        if (r.get("is_selftest") or "").lower() in ("yes", "true", "1"):
            dropped.append((r.get("participant_id"), "selftest row"))
            continue
        if tag and tag != a.study_tag:
            dropped.append((r.get("participant_id"), "study tag %r, not this study" % tag))
            continue

        sides, problems = {}, []
        for s in (1, 2):
            k = r.get("slot%d_key" % s, "")
            info = KEY.get(k)
            if not info:
                problems.append("position %d key %r is not in the decode key" % (s, k))
                continue
            dur = num(field(r, "s%d_duration_sec" % s), 0) or 0
            got = (field(r, "s%d_codeword" % s) or "").strip().lower()
            want = (info.get("codeword") or "").strip().lower()
            pct = num(field(r, "s%d_watch_pct" % s), 0) or 0
            pct = pct * 100 if pct <= 1 else pct
            rate = num(field(r, "s%d_max_rate" % s), 1) or 1
            if want and got != want:
                problems.append("wrong code word at position %d" % s)
            if pct < 85:
                problems.append("only %.0f%% watched at position %d" % (pct, s))
            if rate > 1.25:
                problems.append("played position %d at %.2fx" % (rate and s, rate))
            sides[info["version"]] = {
                "slot": s, "key": k, "pct": pct, "dur": dur, "rate": rate,
                "cw_ok": (not want) or got == want, "cw": got,
                "overall": field(r, "s%d_overall" % s),
                "audio": field(r, "s%d_audio" % s),
                "visuals": field(r, "s%d_visuals" % s),
                "audio_why": field(r, "s%d_audio_why" % s),
                "seek": field(r, "s%d_seek_fwd" % s),
            }
        if "old" not in sides or "new" not in sides:
            dropped.append((r.get("participant_id"), "; ".join(problems) or "could not decode both positions"))
            continue

        wk = r.get("h2h_choice_key", "")
        winfo = KEY.get(wk)
        if not winfo:
            problems.append("head-to-head choice %r is not in the decode key" % wk)
        tot = num(r.get("total_ms"), 0) or 0
        clips = (sides["old"]["dur"] or 0) + (sides["new"]["dur"] or 0)
        floor = max(480, clips * 0.85)
        if tot and tot / 1000 < floor:
            problems.append("session %.0f min, needs %.0f min for the video served"
                            % (tot / 60000, floor / 60))
        cards.append({
            "pid": r.get("participant_id"), "pair": r.get("pair_id"),
            "cc": r.get("cc_code"), "form": r.get("form_version"),
            "old": sides["old"], "new": sides["new"],
            "winner": winfo["version"] if winfo else None,
            "mag": field(r, "h2h_magnitude"),
            "why": r.get("h2h_why"), "standby": field(r, "standby"),
            "general": r.get("s1_comment"), "other": r.get("h2h_other"),
            "mins": tot / 60000 if tot else None,
            "assign": r.get("assign_source"),
            "resumed": field(r, "resumed_from_save"),
            "problems": problems,
        })
        if not problems:
            kept.append(cards[-1])

    # ---- summary over the CLEAN rows only -----------------------------------
    def mean(vals):
        vals = [v for v in vals if v is not None]
        return statistics.mean(vals) if vals else None

    wins = sum(1 for c in kept if c["winner"] == "new")
    per_pair = {}
    for c in kept:
        d = per_pair.setdefault(c["pair"], {"n": 0, "new": 0, "cc": c["cc"]})
        d["n"] += 1
        d["new"] += 1 if c["winner"] == "new" else 0

    rowsout = []
    for metric in ("overall", "audio", "visuals"):
        o = mean([num(c["old"][metric]) for c in kept])
        n = mean([num(c["new"][metric]) for c in kept])
        rowsout.append((metric, o, n, (n - o) if (o is not None and n is not None) else None))

    LABEL = {"overall": "Overall", "audio": "Narration", "visuals": "On-screen"}

    def side_block(c, version):
        s = c[version]
        cls = "new" if version == "new" else "old"
        name = "RECREATION (new)" if version == "new" else "ARCHIVE (old)"
        why = ("<div class='why'><span class='wl'>on the narration:</span> &ldquo;%s&rdquo;</div>"
               % esc(s["audio_why"])) if s["audio_why"] else ""
        return f"""
        <div class="side {cls}">
          <div class="sname">{name}</div>
          <div class="seen">they saw this <strong>{'first' if s['slot']==1 else 'second'}</strong>
            &middot; key {esc(s['key'])}</div>
          <div class="scores">
            <span><b>{esc(s['overall'] or '-')}</b> overall</span>
            <span><b>{esc(s['audio'] or '-')}</b> narration</span>
            <span><b>{esc(s['visuals'] or '-')}</b> on-screen</span>
          </div>
          <div class="meta">watched {s['pct']:.0f}% &middot; {s['rate']:.2f}x &middot;
            code word {'ok' if s['cw_ok'] else 'WRONG'}</div>
          {why}
        </div>"""

    card_html = []
    for c in sorted(cards, key=lambda x: (bool(x["problems"]), x["pair"] or "", x["pid"] or "")):
        picked = ("RECREATION" if c["winner"] == "new"
                  else "ARCHIVE" if c["winner"] == "old" else "NOT RECORDED")
        pcls = "pnew" if c["winner"] == "new" else "pold" if c["winner"] == "old" else "pnone"
        agree = None
        so, sn = num(c["old"]["overall"]), num(c["new"]["overall"])
        if so is not None and sn is not None and c["winner"]:
            higher = "new" if sn > so else "old" if so > sn else None
            agree = (higher == c["winner"]) if higher else None
        agree_html = ("" if agree is None else
                      "<span class='ag ok'>ratings agree with the pick</span>" if agree
                      else "<span class='ag no'>rated the other one higher</span>")
        probs = ("<div class='probs'><strong>Excluded:</strong> " +
                 "; ".join(esc(p) for p in c["problems"]) + "</div>") if c["problems"] else ""
        blocks = side_block(c, "new") + side_block(c, "old")
        extra = ""
        if c["why"]:
            # Raters write "the first one" / "the second one" in free text, and the reader
            # then has to map that back to old vs new. Spell the mapping out beside the
            # quote rather than making them look back up at the header, because this is
            # exactly where a comment gets attached to the wrong version.
            firstv = "recreation" if c["new"]["slot"] == 1 else "archive"
            secondv = "archive" if c["new"]["slot"] == 1 else "recreation"
            extra += (f"<div class='q'><span class='ql'>why that one &nbsp;&middot;&nbsp; "
                      f"for this rater &ldquo;the first&rdquo; = {firstv}, "
                      f"&ldquo;the second&rdquo; = {secondv}</span>"
                      f"&ldquo;{esc(c['why'])}&rdquo;</div>")
        if c["general"]:
            extra += f"<div class='q'><span class='ql'>closing comment (whole study, not one video)</span>&ldquo;{esc(c['general'])}&rdquo;</div>"
        if c["other"]:
            extra += f"<div class='q'><span class='ql'>anything else</span>&ldquo;{esc(c['other'])}&rdquo;</div>"
        card_html.append(f"""
      <article class="card {'bad' if c['problems'] else ''}">
        <header>
          <span class="pid">{esc(c['pid'])}</span>
          <span class="pair">{esc(c['pair'])} &middot; {esc(c['cc'])}</span>
          <span class="spacer"></span>
          <span class="pick {pcls}">picked {picked}</span>
          <span class="mag">{esc(c['mag'] or '')}</span>
        </header>
        {probs}
        <div class="sides">{blocks}</div>
        {agree_html}
        {extra}
        <footer>
          would train a coworker with their pick: <strong>{esc(c['standby'] or '-')}</strong>
          &middot; session {('%.0f min' % c['mins']) if c['mins'] else '?'}
          &middot; assignment {esc(c['assign'] or '?')}
          {'&middot; <strong>resumed</strong>' if str(c['resumed']).lower()=='yes' else ''}
        </footer>
      </article>""")

    pair_rows = "".join(
        f"<tr><td>{esc(p)}</td><td>{esc(d['cc'])}</td><td>{d['new']} of {d['n']}</td>"
        f"<td>{'recreation ahead' if d['new']*2>d['n'] else 'archive ahead' if d['new']*2<d['n'] else 'tied'}</td></tr>"
        for p, d in sorted(per_pair.items()))
    metric_rows = "".join(
        f"<tr><td>{LABEL[m]}</td><td>{'-' if o is None else '%.2f'%o}</td>"
        f"<td>{'-' if n is None else '%.2f'%n}</td>"
        f"<td class='{'up' if (d or 0)>0 else 'down' if (d or 0)<0 else ''}'>"
        f"{'-' if d is None else '%+.2f'%d}</td></tr>"
        for m, o, n, d in rowsout)
    drop_rows = "".join(f"<li>{esc(p)}: {esc(w)}</li>" for p, w in dropped) or "<li>none</li>"

    doc = f"""<!doctype html><meta charset="utf-8">
<title>Rater pilot results</title>
<style>
 :root {{ --new:#1b7f4b; --old:#8a5a00; --bg:#fbfbfa; --ink:#1b1b1b; --mut:#6b6b6b;
          --line:#e3e3e0; }}
 * {{ box-sizing:border-box }}
 body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 -apple-system,
        BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; }}
 .wrap {{ max-width:1000px; margin:0 auto; padding:28px 20px 80px }}
 h1 {{ font-size:24px; margin:0 0 4px }}
 .sub {{ color:var(--mut); margin:0 0 22px }}
 .banner {{ background:#fff5d6; border:1px solid #e8d48a; padding:12px 14px;
            border-radius:8px; margin:0 0 24px; font-size:14px }}
 h2 {{ font-size:16px; text-transform:uppercase; letter-spacing:.06em; color:var(--mut);
       margin:32px 0 10px }}
 /* Narrow screens scroll a table rather than crushing its columns into each other. */
 .tw {{ overflow-x:auto; -webkit-overflow-scrolling:touch }}
 table {{ border-collapse:collapse; width:100%; min-width:460px; background:#fff;
          border:1px solid var(--line); border-radius:8px; font-size:14px }}
 td,th {{ white-space:nowrap }}
 th,td {{ text-align:left; padding:9px 12px; border-bottom:1px solid var(--line) }}
 th {{ background:#f4f4f2; font-weight:600 }}
 tr:last-child td {{ border-bottom:0 }}
 td.up {{ color:var(--new); font-weight:700 }} td.down {{ color:#b3261e; font-weight:700 }}
 .headline {{ background:#fff; border:1px solid var(--line); border-radius:8px;
              padding:16px 18px; font-size:15px }}
 .big {{ font-size:30px; font-weight:700; letter-spacing:-.02em }}
 .card {{ background:#fff; border:1px solid var(--line); border-radius:10px;
          padding:14px 16px; margin:12px 0 }}
 .card.bad {{ background:#fff7f6; border-color:#f0c8c2 }}
 .card header {{ display:flex; gap:10px; align-items:center; flex-wrap:wrap;
                 padding-bottom:10px; border-bottom:1px solid var(--line); margin-bottom:12px }}
 .pid {{ font-weight:700 }} .pair {{ color:var(--mut); font-size:13px }}
 .spacer {{ flex:1 }}
 .pick {{ font-size:12px; font-weight:700; padding:3px 9px; border-radius:99px; color:#fff }}
 .pnew {{ background:var(--new) }} .pold {{ background:var(--old) }} .pnone {{ background:#999 }}
 .mag {{ font-size:12px; color:var(--mut) }}
 .sides {{ display:grid; grid-template-columns:1fr 1fr; gap:12px }}
 @media (max-width:700px) {{ .sides {{ grid-template-columns:1fr }} }}
 .side {{ border:1px solid var(--line); border-left-width:4px; border-radius:8px; padding:10px 12px }}
 .side.new {{ border-left-color:var(--new) }} .side.old {{ border-left-color:var(--old) }}
 .sname {{ font-size:11px; font-weight:800; letter-spacing:.08em }}
 .side.new .sname {{ color:var(--new) }} .side.old .sname {{ color:var(--old) }}
 .seen {{ font-size:12px; color:var(--mut); margin:2px 0 8px }}
 .scores {{ display:flex; gap:14px; flex-wrap:wrap; font-size:12px; color:var(--mut) }}
 .scores b {{ font-size:19px; color:var(--ink) }}
 .meta {{ font-size:12px; color:var(--mut); margin-top:8px }}
 .why {{ margin-top:8px; font-size:13px; background:#f7f7f5; padding:7px 9px; border-radius:6px }}
 .wl {{ display:block; font-size:11px; text-transform:uppercase; letter-spacing:.05em;
        color:var(--mut) }}
 .ag {{ display:inline-block; margin-top:10px; font-size:12px; padding:2px 8px;
        border-radius:99px }}
 .ag.ok {{ background:#e7f3ec; color:var(--new) }}
 .ag.no {{ background:#fdeceb; color:#b3261e }}
 .q {{ margin-top:10px; font-size:14px; background:#f7f7f5; padding:9px 11px; border-radius:6px }}
 .ql {{ display:block; font-size:11px; text-transform:uppercase; letter-spacing:.05em;
        color:var(--mut); margin-bottom:2px }}
 .probs {{ background:#fdeceb; color:#8c1d18; padding:8px 10px; border-radius:6px;
           font-size:13px; margin-bottom:12px }}
 .card footer {{ margin-top:12px; padding-top:9px; border-top:1px solid var(--line);
                 font-size:12px; color:var(--mut) }}
 ul.drop {{ font-size:13px; color:var(--mut) }}
</style>
<div class="wrap">
  <h1>Rater pilot results</h1>
  <p class="sub">{len(cards)} decoded &middot; {len(kept)} clean &middot; study tag {esc(a.study_tag)}</p>

  <div class="banner"><strong>Reading this page.</strong> Raters saw the two videos in
  alternating order, so &ldquo;first&rdquo; is the recreation for about half of them and the
  archive for the rest. On every card the <strong>recreation is always the left block and
  always green</strong>, the archive always right and amber, whatever order that person
  actually watched. The line under each heading says which position they saw it in.
  This file contains the blind. Do not share it outside the team.</div>

  <h2>Headline</h2>
  <div class="headline">
    <div><span class="big">{wins} of {len(kept)}</span> clean raters preferred the
      <strong>recreation</strong>
      {'' if not kept else '(%.0f%%)' % (wins / len(kept) * 100)}</div>
  </div>

  <h2>Mean ratings, clean rows</h2>
  <div class="tw"><table><tr><th>Question</th><th>Archive</th><th>Recreation</th>
  <th>Difference</th></tr>
  {metric_rows}</table></div>

  <h2>By pair</h2>
  <div class="tw"><table><tr><th>Pair</th><th>Course</th><th>Chose the recreation</th>
  <th></th></tr>
  {pair_rows}</table></div>

  <h2>Every rater</h2>
  {''.join(card_html)}

  <h2>Not counted</h2>
  <ul class="drop">{drop_rows}</ul>
</div>
"""
    open(a.out, "w", encoding="utf-8").write(doc)
    print("wrote %s (%d decoded, %d clean, %d not counted)"
          % (a.out, len(cards), len(kept), len(dropped)))


if __name__ == "__main__":
    main()
