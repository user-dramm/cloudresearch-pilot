#!/usr/bin/env bash
# Copy the instrument into demo/ so the preview build cannot drift from the real one.
#
#   ./tools/sync_demo.sh
#
# WHY THIS EXISTS
# ---------------
# The preview at /demo/ has to be the SAME index.html as the study at the site
# root, differing only in its config.js. If the two HTML files are edited
# separately they drift, and then colleagues review questions that are not the ones
# a paid rater will see - which is worse than not previewing at all, because it
# produces confident feedback about the wrong instrument.
#
# So demo/index.html is GENERATED, never edited. Run this after any change to
# index.html and before pushing.

set -euo pipefail
cd "$(dirname "$0")/.."

[ -f index.html ] || { echo "index.html not found - run from the repo"; exit 1; }
mkdir -p demo
cp index.html demo/index.html

if [ ! -f demo/config.js ]; then
  echo "WARNING: demo/config.js is missing. The preview will not run."
  exit 1
fi

# The one thing that must differ, checked rather than assumed: a demo that carries
# the real study tag would put preview rows into the analysed dataset.
real=$(grep -oE 'studyTag:[[:space:]]*"[^"]*"' config.js | head -1)
demo=$(grep -oE 'studyTag:[[:space:]]*"[^"]*"' demo/config.js | head -1)
echo "  study : $real"
echo "  demo  : $demo"
if [ "$real" = "$demo" ]; then
  echo "  *** STOP: demo/config.js carries the real studyTag. Preview rows would be"
  echo "      analysed as real responses. Change studyTag in demo/config.js."
  exit 1
fi

echo "  demo/index.html synced from index.html"
