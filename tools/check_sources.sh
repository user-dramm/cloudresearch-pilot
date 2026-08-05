#!/usr/bin/env bash
# Pre-flight check on the source videos downloaded out of Synthesia (and wherever the
# old versions came from), BEFORE any clip gets built.
#
#   ./tools/check_sources.sh /path/to/downloads
#
# WHY THIS EXISTS
# ---------------
# Raters are scoring visual quality. `make_clips.sh` normalises encoding so your encoder
# can't become the thing being measured - but it cannot fix a source problem. If the old
# version of a course is 480p 4:3 with quiet audio and the new one is 1080p 16:9, raters
# will reliably prefer the new one and you will have measured the upgrade in render
# settings rather than the pipeline. That result would pass the pre-registered criterion
# and be worthless.
#
# This script surfaces that before you spend anything. It reports every file, then flags
# pairs whose old and new sides differ in ways that could bias the comparison.
#
# Name files so the pair and side are unambiguous, e.g.
#   00158_old_mod1.mp4   00158_old_mod3.mp4
#   00158_new_mod1.mp4   00158_new_mod3.mp4

set -uo pipefail
DIR="${1:?usage: check_sources.sh <folder of source videos>}"
CODES="${CODES:-00051 00158 00162 00175 00254}"

command -v ffprobe >/dev/null || { echo "ffprobe not found. brew install ffmpeg"; exit 1; }

probe() { ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate \
  -show_entries format=duration -of default=nw=1:nk=1 "$1" 2>/dev/null; }
has_audio() { ffprobe -v error -select_streams a -show_entries stream=index \
  -of csv=p=0 "$1" 2>/dev/null | head -1; }
loudness() { ffmpeg -hide_banner -nostats -i "$1" -af ebur128 -f null - 2>&1 \
  | awk '/I:/{v=$2} END{print v}'; }

echo "======================================================================"
echo "SOURCE VIDEO PRE-FLIGHT   $DIR"
echo "======================================================================"
printf "%-34s %9s %11s %6s %6s\n" "file" "duration" "size" "fps" "audio"
echo "----------------------------------------------------------------------"

found=0
for f in "$DIR"/*.mp4 "$DIR"/*.mov "$DIR"/*.MP4 "$DIR"/*.webm; do
  [ -e "$f" ] || continue
  found=$((found+1))
  read -r W H FPS DUR <<<"$(probe "$f" | paste -sd' ' -)"
  A=$([ -n "$(has_audio "$f")" ] && echo yes || echo "NONE")
  printf "%-34s %8.1fs %11s %6s %6s\n" \
    "$(basename "$f" | cut -c1-34)" "${DUR:-0}" "${W:-?}x${H:-?}" \
    "$(echo "${FPS:-0}" | awk -F/ '{if($2)printf "%.0f",$1/$2; else print $1}')" "$A"
done

if [ "$found" -eq 0 ]; then
  echo "  no video files found in $DIR"
  exit 1
fi

echo
echo "======================================================================"
echo "PAIR PARITY  — old vs new of the same course must be comparable"
echo "======================================================================"

flags=0
for code in $CODES; do
  olds=$(ls "$DIR" 2>/dev/null | grep -i "$code" | grep -i "old" || true)
  news=$(ls "$DIR" 2>/dev/null | grep -i "$code" | grep -i "new" || true)

  if [ -z "$olds" ] && [ -z "$news" ]; then
    printf "  %-8s  nothing found — pair not staged\n" "$code"; continue
  fi
  if [ -z "$olds" ]; then
    printf "  %-8s  BLOCKER: no OLD version. This pair cannot run.\n" "$code"
    flags=$((flags+1)); continue
  fi
  if [ -z "$news" ]; then
    printf "  %-8s  waiting: no NEW version yet\n" "$code"; continue
  fi

  sum() { local t=0 d; for n in $1; do
    d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$DIR/$n" 2>/dev/null)
    t=$(awk -v a="$t" -v b="${d:-0}" 'BEGIN{print a+b}'); done; echo "$t"; }
  res() { ffprobe -v error -select_streams v:0 -show_entries stream=width,height \
    -of csv=p=0:s=x "$DIR/$(echo "$1" | head -1)" 2>/dev/null; }

  od=$(sum "$olds"); nd=$(sum "$news")
  ores=$(res "$olds"); nres=$(res "$news")
  gap=$(awk -v a="$od" -v b="$nd" 'BEGIN{d=a-b; if(d<0)d=-d; if(a>0)printf "%.0f", 100*d/a; else print 999}')

  printf "  %-8s  old %2d file(s) %6.1fs %-10s | new %2d file(s) %6.1fs %-10s" \
    "$code" "$(echo "$olds" | wc -w)" "$od" "$ores" "$(echo "$news" | wc -w)" "$nd" "$nres"

  note=""
  [ "$ores" != "$nres" ] && { note="$note  RESOLUTION MISMATCH"; flags=$((flags+1)); }
  [ "$gap" -gt 25 ] 2>/dev/null && { note="$note  DURATION GAP ${gap}%"; flags=$((flags+1)); }
  echo "$note"
done

echo
if [ "$flags" -eq 0 ]; then
  echo "No parity problems found. Safe to run make_clips.sh."
else
  echo "$flags flag(s) above. Read them before cutting clips."
  echo
  echo "  RESOLUTION MISMATCH — make_clips.sh will scale both sides to a common target,"
  echo "  which keeps framing matched, but an upscaled 480p source will still look softer"
  echo "  than a native 1080p one. Raters will notice, and you will have measured the"
  echo "  render settings rather than the pipeline. Try to source a better copy of the old"
  echo "  version first. If you can't, say so plainly in the writeup - it is a real"
  echo "  confound, not a footnote."
  echo
  echo "  DURATION GAP >25% — the two sides may not be the same content. Check you matched"
  echo "  by topic rather than by module number; a recreated course often renumbers."
fi
