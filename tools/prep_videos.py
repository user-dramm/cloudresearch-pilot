#!/usr/bin/env python3
"""
Prepare a course pair for upload: four videos, code word burned into the second.

    python3 tools/prep_videos.py --src "~/Downloads/pilot_build/src/Cloud Courses" \
                                 --out ~/Downloads/pilot_build/out \
                                 --map map.json [--course 158] [--dry-run]

Input layout, one folder per course, four files in each:

    158/1 - Course Overview(old).mp4     <- archived version, module 1
    158/1 - Course Overview.mp4          <- current version, module 1
    158/3 - Something (old).mp4          <- archived version, module 3
    158/3 - Something.mp4                <- current version, module 3

"(old)" anywhere in the filename marks the archived side, with or without a space
before the bracket. Anything without it is the current build.

Output, named only by the OPAQUE KEY so nothing on disk or in a URL says old or new:

    out/k5qd_v1.mp4   out/k5qd_v2.mp4      <- one version's two videos
    out/k2wj_v1.mp4   out/k2wj_v2.mp4      <- the other version's two

WHAT THIS DOES AND WHY
----------------------
1. Every one of the four goes through IDENTICAL encode settings. Raters score
   visual quality, so if the two sides were encoded differently part of what they
   score is the encoder. Identical settings mean this step adds no difference. It
   cannot remove a difference already baked into a source - measured on this
   material at SSIM 0.99+, so the sources are perceptually equivalent anyway.

2. A code word is drawn on the SECOND video only, at 45% of the way through, for
   five seconds. Second rather than first on purpose: the watch gate already proves
   a video played, so the code word's job is proving the rater was still watching
   near the end of the set, which is where attention goes.

3. `+faststart` so a self-hosted mp4 starts playing before it has fully
   downloaded. Without it a rater stares at a black box long enough to abandon.

Needs ffmpeg. Pass --ffmpeg if it is not on PATH.
"""

import argparse, json, os, re, subprocess, sys

# Deliberately NOT the words in decode_key.example.json. That file is tracked by
# git and public, so reusing its words would publish the answers - and knowing a
# code word lets someone claim they watched when they did not.
WORD_POOL = ["cobalt", "juniper", "sandbar", "kettle", "driftwood",
             "saffron", "lattice", "ironwood", "marlin", "plumline"]

VIDEO_RE = re.compile(r"^\s*(\d+)\s*-\s*(.+?)\s*(\(old\))?\.mp4$", re.I)


def find_pairs(course_dir):
    """-> {'old': {1: path, 3: path}, 'new': {1: path, 3: path}}"""
    found = {"old": {}, "new": {}}
    for name in sorted(os.listdir(course_dir)):
        if not name.lower().endswith(".mp4"):
            continue
        m = VIDEO_RE.match(name)
        if not m:
            print("    ! skipped, unrecognised name: %s" % name)
            continue
        mod = int(m.group(1))
        side = "old" if m.group(3) else "new"
        if mod in found[side]:
            print("    ! two files claim %s module %d - %s" % (side, mod, name))
        found[side][mod] = os.path.join(course_dir, name)
    return found


def duration(ffmpeg, path):
    out = subprocess.run([ffmpeg, "-hide_banner", "-i", path],
                         capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
    if not m:
        return None
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def encode(ffmpeg, src, dst, word=None, at=None, fontfile=None,
           crf=20, preset="veryfast", w=1920, h=1080, fps=30):
    """Identical settings for every clip. `word` draws the code word if given."""
    vf = ("scale=%d:%d:force_original_aspect_ratio=decrease,"
          "pad=%d:%d:-1:-1:color=black,setsar=1,fps=%d" % (w, h, w, h, fps))
    if word:
        # Escape for drawtext: colon and backslash are both filter syntax.
        safe = word.replace("\\", "\\\\").replace(":", r"\:").replace("'", r"\'")
        # The font is pinned rather than left to fontconfig. This ffmpeg build has
        # no fontconfig config file, so the default face is whatever it happens to
        # find - which could differ between machines or silently fail, and a code
        # word that did not render is a question no rater can answer.
        font = ("fontfile='%s':" % fontfile) if fontfile else ""
        # TOP centre, not bottom. The recreated videos carry burned-in captions
        # along the bottom and the Embrace logo sits bottom-right, so a bottom
        # overlay lands on top of the caption and both become hard to read - which
        # turns a proof-of-watching question into a guess. The avatar circle sits
        # top-RIGHT, so top-centre is clear on both sides of every pair.
        vf += (",drawtext=%stext='Code word\\: %s'"
               ":fontcolor=white:fontsize=44:box=1:boxcolor=black@0.72:boxborderw=16"
               ":x=(w-text_w)/2:y=52:enable='between(t,%.2f,%.2f)'"
               % (font, safe, at, at + 5))
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", src,
           "-vf", vf,
           "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
           "-movflags", "+faststart", dst]
    subprocess.run(cmd, check=True)


def verify_codeword(ffmpeg, out_path, src_path, at):
    """Confirm the overlay rendered, by comparing the output against its OWN SOURCE
    at the same timestamp, cropped to where the box is drawn.

    An earlier version of this compared bright-pixel counts inside the code-word
    window against a frame outside it, and reported every file as a failure. That
    was wrong: the bottom of these frames carries slide titles and a logo, so the
    baseline swings by thousands of pixels between any two timestamps and swamps
    the overlay. Output-versus-source at the SAME instant differs by nothing except
    the overlay, so it cannot be fooled by content.

    A silent drawtext failure would otherwise ship a video whose code-word question
    no rater can answer, and there is no way to tell after upload.
    """
    def strip(path, t):
        # Accurate seek: -ss AFTER -i decodes up to the timestamp. With -ss before
        # -i ffmpeg seeks to the nearest keyframe, and since re-encoding moves the
        # keyframes, output and source landed on DIFFERENT frames - which made this
        # comparison meaningless and produced false failures.
        # Region: top strip, centre 60%, where the box is drawn.
        p = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error",
                            "-i", path, "-ss", "%.2f" % t, "-frames:v", "1",
                            "-vf", "scale=960:540,crop=576:80:192:14,format=gray",
                            "-f", "rawvideo", "-"], capture_output=True)
        return p.stdout

    a, b = strip(out_path, at + 2.0), strip(src_path, at + 2.0)
    if not a or not b or len(a) != len(b):
        return None, None
    changed = sum(1 for x, y in zip(a, b) if abs(x - y) > 40)
    return changed, len(a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="folder containing one folder per course")
    ap.add_argument("--out", required=True)
    ap.add_argument("--map", default="prep_map.json",
                    help="where to write the key -> side/codeword mapping")
    ap.add_argument("--course", action="append",
                    help="only this course folder (repeatable); default all")
    ap.add_argument("--keys", default="",
                    help="comma-separated opaque keys to use, in course order, "
                         "two per course. Default: read from config.js order.")
    ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--fontfile", default="/System/Library/Fonts/Supplemental/Arial.ttf",
                    help="pinned rather than left to fontconfig, so the overlay cannot "
                         "silently fail or change face between machines")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not a.dry_run and a.fontfile and not os.path.exists(a.fontfile):
        sys.exit("fontfile not found: %s (pass --fontfile)" % a.fontfile)

    src = os.path.expanduser(a.src)
    out = os.path.expanduser(a.out)
    courses = sorted(d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d)))
    if a.course:
        courses = [c for c in courses if c in a.course]

    keys = [k.strip() for k in a.keys.split(",") if k.strip()]
    mapping, wi, ki = {}, 0, 0
    ready, skipped = [], []

    for c in courses:
        cdir = os.path.join(src, c)
        found = find_pairs(cdir)
        have = {s: sorted(found[s]) for s in ("old", "new")}
        if not (1 in found["old"] and 3 in found["old"]
                and 1 in found["new"] and 3 in found["new"]):
            skipped.append("%s: old has %s, new has %s - needs modules 1 and 3 on both"
                           % (c, have["old"] or "nothing", have["new"] or "nothing"))
            continue
        ready.append((c, found))

    print("=" * 78)
    print("PREP  %d course(s) ready, %d incomplete" % (len(ready), len(skipped)))
    print("=" * 78)
    for s in skipped:
        print("  skip  %s" % s)
    if not ready:
        sys.exit("\nNothing to do.")

    os.makedirs(out, exist_ok=True)
    for c, found in ready:
        print("\n  course %s" % c)
        # Randomising which side gets the first key is done by the caller passing
        # keys in the intended order; this loop keeps a fixed old,new order so the
        # mapping written out is unambiguous.
        for side in ("old", "new"):
            key = keys[ki] if ki < len(keys) else "%s_%s" % (c, side)
            ki += 1
            word = WORD_POOL[wi % len(WORD_POOL)]; wi += 1
            m1, m3 = found[side][1], found[side][3]
            d3 = duration(a.ffmpeg, m3) or 0
            at = round(d3 * 0.45, 2)

            print("    %-6s key %-10s code word %-10s on video 2 at %.0fs of %.0fs"
                  % (side, key, word, at, d3))
            print("           v1  %s" % os.path.basename(m1))
            print("           v2  %s" % os.path.basename(m3))

            mapping[key] = {"version": side, "pair_folder": c, "codeword": word,
                            "video1": os.path.basename(m1),
                            "video2": os.path.basename(m3),
                            "codeword_at_sec": at}
            if a.dry_run:
                continue
            encode(a.ffmpeg, m1, os.path.join(out, "%s_v1.mp4" % key))
            v2 = os.path.join(out, "%s_v2.mp4" % key)
            encode(a.ffmpeg, m3, v2, word=word, at=at, fontfile=a.fontfile)
            for suffix in ("v1", "v2"):
                p = os.path.join(out, "%s_%s.mp4" % (key, suffix))
                print("           -> %s  %.0f MB" % (os.path.basename(p),
                                                     os.path.getsize(p) / 1e6))
            changed, total = verify_codeword(a.ffmpeg, v2, m3, at)
            if changed is None:
                print("           code word check: could not compare frames")
            else:
                pct = changed / total * 100
                good = pct > 3.0
                print("           code word check: %.1f%% of the overlay region differs "
                      "from the source  -> %s"
                      % (pct, "VISIBLE" if good else "*** NOT VISIBLE ***"))
                if not good:
                    print("           *** the overlay did not render. Do not upload this file.")

    with open(os.path.expanduser(a.map), "w") as f:
        json.dump(mapping, f, indent=1)
    print("\n  mapping written to %s" % a.map)
    print("  THIS FILE IS THE BLIND. It says which key is old and which is new.")
    print("  Fold it into decode_key.json and never commit either.")


if __name__ == "__main__":
    main()
