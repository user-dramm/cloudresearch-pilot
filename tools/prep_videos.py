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

Output, as module - padded course code - opaque key, with -cw where a code word was
burned in:

    out/1-00158-k5qd.mp4   out/3-00158-k5qd-cw.mp4     <- one version's two videos
    out/1-00158-k2wj.mp4   out/3-00158-k2wj-cw.mp4     <- the other version's two

The key is in the name because both sides hold a module 3 of the same course, so
course and module alone cannot tell them apart. Nothing in the name says old or new.

THE YOUTUBE TITLE IS NOT THE FILENAME. A YouTube title is visible inside the embed,
so it must carry nothing identifying at all - upload each file under its key and
index (k5qd-1, k5qd-2), which the mapping records as youtube_title_1/2.

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

# Overlay geometry, in 1920x1080 coordinates. SHARED between the encoder and the
# verifier on purpose: the verifier crops to where the box should be, and when these
# were two separate hardcoded numbers, moving the overlay silently made the check
# examine empty frame and report every file as a failure. Change it here only.
OVERLAY_Y  = 300     # top edge of the box. Upper third: clear of the orange callout
                     # panel across the middle-right and the captions along the bottom.
OVERLAY_PT = 44      # font size
OVERLAY_PAD = 16     # box border width


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
               ":fontcolor=white:fontsize=%d:box=1:boxcolor=black@0.72:boxborderw=%d"
               ":x=(w-text_w)/2:y=%d:enable='between(t,%.2f,%.2f)'"
               % (font, safe, OVERLAY_PT, OVERLAY_PAD, OVERLAY_Y, at, at + 5))
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
        # Crop derived from OVERLAY_Y so it always looks where the box actually is.
        # Half scale, so 1080 coordinates halve.
        box_h = OVERLAY_PT + OVERLAY_PAD * 2
        y = max(0, OVERLAY_Y // 2 - 6)
        h = box_h // 2 + 16
        p = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error",
                            "-i", path, "-ss", "%.2f" % t, "-frames:v", "1",
                            "-vf", "scale=960:540,crop=576:%d:192:%d,format=gray" % (h, y),
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
    ap.add_argument("--assign", action="append", default=[], metavar="SPEC",
                    help="explicit per-course assignment, repeatable:\n"
                         "  --assign '158=old:k5qd:cobalt,new:k2wj:juniper'\n"
                         "Naming the course, the side, the opaque key and the code word "
                         "together is deliberate. An earlier version took two parallel "
                         "lists positionally and relied on courses being iterated in the "
                         "order they were given - but they are iterated SORTED, so '176' "
                         "came before '51' and every key landed on the wrong course. "
                         "That is the one error this study would report confidently in "
                         "the wrong direction, so ordering is now impossible to get "
                         "wrong: nothing is implied by position.")
    ap.add_argument("--side", choices=("old", "new"),
                    help="process only this side. For when the other side is already "
                         "encoded and uploaded: re-running it would overwrite finished "
                         "files for no gain, and the encode is deterministic so the "
                         "output would be identical anyway.")
    ap.add_argument("--allow-partial", action="store_true",
                    help="process a side that has modules 1 and 3 even when the other "
                         "side is missing. For pairs whose new version is still being "
                         "built - the archived side can be embedded and uploaded now.")
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

    # {course: {side: (key, word)}} - parsed from --assign, no positional meaning.
    assign = {}
    for spec in a.assign:
        if "=" not in spec:
            sys.exit("bad --assign %r, expected COURSE=side:key:word,side:key:word" % spec)
        course, rest = spec.split("=", 1)
        for part in rest.split(","):
            bits = part.split(":")
            if len(bits) != 3 or bits[0] not in ("old", "new"):
                sys.exit("bad --assign entry %r, expected old|new:key:word" % part)
            assign.setdefault(course.strip(), {})[bits[0]] = (bits[1].strip(), bits[2].strip())

    # Merge, never overwrite. The map is the blind, and it is built up across runs
    # as sides become available - clobbering it would lose the old/new mapping for
    # pairs processed earlier, which is unrecoverable once the sources are gone.
    map_path = os.path.expanduser(a.map)
    mapping = {}
    if os.path.exists(map_path):
        try:
            mapping = json.load(open(map_path))
            print("  merging into existing map (%d key(s) already recorded)" % len(mapping))
        except ValueError:
            sys.exit("existing map at %s is not valid JSON - move it aside" % map_path)

    wi = 0
    ready, skipped = [], []

    for c in courses:
        cdir = os.path.join(src, c)
        found = find_pairs(cdir)
        have = {s: sorted(found[s]) for s in ("old", "new")}
        # `available` is what the SOURCE holds; `complete` is what this run will encode.
        # Keeping them apart matters: a side excluded by --side is finished work being
        # left alone, not a missing source, and must not be stamped RESERVED in the map.
        available = {s for s in ("old", "new") if 1 in found[s] and 3 in found[s]}
        found["_available"] = available
        complete = set(available)
        if a.side:
            complete &= {a.side}
        if len(complete) == 2:
            ready.append((c, found, ["old", "new"]))
        elif complete and (a.allow_partial or a.side):
            ready.append((c, found, sorted(complete)))
            other = sorted({"old", "new"} - complete)
            why = ("excluded by --side, already done" if set(other) <= available
                   else "source not supplied")
            skipped.append("%s: doing the %s side only (%s: %s)"
                           % (c, "/".join(sorted(complete)), "/".join(other), why))
        else:
            skipped.append("%s: old has %s, new has %s - needs modules 1 and 3%s"
                           % (c, have["old"] or "nothing", have["new"] or "nothing",
                              " on both (pass --allow-partial for one side)"))
            continue

    print("=" * 78)
    print("PREP  %d course(s) ready, %d incomplete" % (len(ready), len(skipped)))
    print("=" * 78)
    for s in skipped:
        print("  skip  %s" % s)
    if not ready:
        sys.exit("\nNothing to do.")

    os.makedirs(out, exist_ok=True)
    for c, found, sides in ready:
        print("\n  course %s" % c)
        for side in ("old", "new"):
            spec = assign.get(c, {}).get(side)
            if spec:
                key, word = spec
            else:
                key = "%s_%s" % (c, side)
                word = WORD_POOL[wi % len(WORD_POOL)]
                wi += 1
            if side not in sides:
                if side in found.get("_available", set()):
                    # Present in the source, just not being encoded this run. Finished
                    # work: leave the map entry exactly as it is. Stamping RESERVED
                    # here would mark already-encoded, already-uploaded videos as
                    # pending in the one file that records which side is which.
                    print("    %-6s key %-10s code word %-10s left alone (--side)"
                          % (side, key, word))
                    continue
                print("    %-6s key %-10s code word %-10s RESERVED - source not supplied yet"
                      % (side, key, word))
                # Record the reservation in the map too, not just on screen. It used
                # to only print, so the reserved key and its code word survived
                # nowhere durable - and the whole point of reserving is that when the
                # render finally arrives weeks later it gets the SAME key and word.
                # A reservation that exists only in a terminal scrollback is not one.
                mapping.setdefault(key, {}).update(
                    {"version": side, "pair_folder": c, "codeword": word,
                     "status": "RESERVED - source not supplied yet"})
                continue
            m1, m3 = found[side][1], found[side][3]
            d3 = duration(a.ffmpeg, m3) or 0
            at = round(d3 * 0.45, 2)

            # Output names are for the human sorting a folder: module number, padded
            # course code, the opaque key, and -cw where a code word was burned in.
            # The KEY has to be in there because both sides hold a module 3 of the
            # same course, so course+module alone is ambiguous - and the key is what
            # distinguishes them without the filename ever saying old or new.
            code = c.zfill(5)
            n1 = "1-%s-%s.mp4" % (code, key)
            n2 = "3-%s-%s-cw.mp4" % (code, key)

            print("    %-6s key %-10s code word %-10s on video 2 at %.0fs of %.0fs"
                  % (side, key, word, at, d3))
            print("           %-26s <- %s" % (n1, os.path.basename(m1)))
            print("           %-26s <- %s" % (n2, os.path.basename(m3)))

            mapping[key] = {"version": side, "pair_folder": c, "codeword": word,
                            "video1": os.path.basename(m1),
                            "video2": os.path.basename(m3),
                            "out_video1": n1, "out_video2": n2,
                            "youtube_title_1": "%s-1" % key,
                            "youtube_title_2": "%s-2" % key,
                            "codeword_at_sec": at}
            if a.dry_run:
                continue
            encode(a.ffmpeg, m1, os.path.join(out, n1))
            v2 = os.path.join(out, n2)
            encode(a.ffmpeg, m3, v2, word=word, at=at, fontfile=a.fontfile)
            for n in (n1, n2):
                p = os.path.join(out, n)
                print("           -> %-26s %.0f MB" % (n, os.path.getsize(p) / 1e6))
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

    if a.dry_run:
        # A dry run must not write. The earlier version did, and a dry run whose
        # assignments turned out to be wrong silently corrupted the real map - the
        # one file that records which side is which and cannot be reconstructed
        # once the sources are gone.
        print("\n  --dry-run: nothing encoded, map NOT written")
        return

    with open(map_path, "w") as f:
        json.dump(mapping, f, indent=1)
    print("\n  mapping written to %s" % map_path)
    print("  THIS FILE IS THE BLIND. It says which key is old and which is new.")
    print("  Fold it into decode_key.json and never commit either.")


if __name__ == "__main__":
    main()
