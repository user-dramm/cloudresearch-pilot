#!/usr/bin/env bash
# Build one pilot clip: module 1 + module 3, concatenated, with the code word
# burned in partway through.
#
#   ./tools/make_clips.sh k5qd meadow path/to/module1.mp4 path/to/module3.mp4
#
# Output: clips/k5qd.mp4
#
# WHY THIS SCRIPT EXISTS, AND WHY YOU SHOULD USE IT FOR ALL TEN CLIPS
# -------------------------------------------------------------------
# Raters are scoring visual quality. If the old clips get encoded differently
# from the new ones - different resolution, bitrate, or scaler - then part of
# what they score is your encoder, not your pipeline. Every clip must go through
# exactly these settings. One script, ten runs, no hand-tuning. If a source file
# is lower resolution than the target it gets upscaled rather than letterboxed
# differently from its pair; that is deliberate, since matched framing matters
# more here than absolute sharpness.

set -euo pipefail

KEY="${1:?usage: make_clips.sh <version-key> <codeword> <module1> <module3>}"
WORD="${2:?missing code word}"
M1="${3:?missing module 1}"
M3="${4:?missing module 3}"

OUT_DIR="${OUT_DIR:-clips}"
W="${W:-1280}"; H="${H:-720}"; FPS="${FPS:-30}"; CRF="${CRF:-21}"
mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/$KEY.mp4"

norm() {  # scale + pad + fixed sar + fixed fps, so concat can't fail on mismatch
  echo "scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:-1:-1:color=black,setsar=1,fps=${FPS}"
}

# code word appears for 5s starting 45% of the way in - past any skimming, well
# before the end, and in a spot a rater who skipped the middle would miss
D1=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$M1")
D3=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$M3")
AT=$(python3 -c "print(round(($D1 + $D3) * 0.45, 2))")

echo "  key        $KEY"
echo "  code word  $WORD  (on screen at ${AT}s for 5s)"
echo "  sources    $(basename "$M1")  +  $(basename "$M3")"

ffmpeg -hide_banner -loglevel error -y \
  -i "$M1" -i "$M3" \
  -filter_complex "\
[0:v]$(norm)[v0];[1:v]$(norm)[v1];\
[0:a]aresample=48000,aformat=channel_layouts=stereo[a0];\
[1:a]aresample=48000,aformat=channel_layouts=stereo[a1];\
[v0][a0][v1][a1]concat=n=2:v=1:a=1[vc][ac];\
[vc]drawtext=text='Code word\\: ${WORD}':\
fontcolor=white:fontsize=34:box=1:boxcolor=black@0.72:boxborderw=14:\
x=(w-text_w)/2:y=h-th-48:enable='between(t,${AT},${AT}+5)'[v]" \
  -map "[v]" -map "[ac]" \
  -c:v libx264 -preset slow -crf "$CRF" -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 48000 \
  -movflags +faststart \
  "$OUT"

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")
SIZE=$(du -h "$OUT" | cut -f1)
printf "  -> %s  %.1f min  %s\n\n" "$OUT" "$(python3 -c "print($DUR/60)")" "$SIZE"

# +faststart matters: without it a self-hosted mp4 won't start playing until the
# whole file has downloaded, which on a 150 MB clip means a rater staring at a
# black box long enough to abandon a $7 session.
