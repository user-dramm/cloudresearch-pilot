#!/usr/bin/env bash
# Run every suite and report honestly. Drives off EXIT CODES only.
#
# An earlier ad-hoc runner matched words in the output instead, and it both flagged
# "17 of 17 edge cases handled without crashing" as a failure (the substring "crash")
# and reported a suite that had crashed on a wrong port as PASSING, because the last
# line was just the Node version. A gate that reports false passes is worse than none,
# so every suite now exits non-zero on failure and this reads nothing but the code.
#
#   ./tools/run_all.sh
#
# Needs PLAYWRIGHT_PATH set for the browser suites, and serves the repo itself.
set -u
cd "$(dirname "$0")/.." || exit 1

PORT="${PORT:-8795}"
export PORT
python3 -m http.server "$PORT" >/dev/null 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
sleep 2

pass=0; fail=0; failed=""
run() {
  local name="$1"; shift
  printf "  %-24s " "$name"
  local out
  out=$("$@" 2>&1)
  if [ $? -eq 0 ]; then
    pass=$((pass+1)); printf "ok    %s\n" "$(echo "$out" | tail -1)"
  else
    fail=$((fail+1)); failed="$failed $name"
    printf "FAIL\n"
    echo "$out" | tail -6 | sed 's|^|        |'
  fi
}

echo "SUITES"
run "consistency"        python3 tools/consistency_check.py
run "edge cases"         python3 tools/test_edge_cases.py
run "report attribution" python3 tools/test_report.py
run "rating attribution" python3 tools/test_attribution.py
run "choice attribution"  node tools/test_choice_attribution.js
run "sheet columns"      node tools/test_headers.js
run "device gating"      node tools/test_devices.js
run "interaction"        node tools/test_interaction.js
run "submit failure"     node tools/test_submit_failure.js
run "anti-cheat"         node tools/test_anticheat.js
run "playback speed"     node tools/test_speed.js

echo
if [ "$fail" -eq 0 ]; then
  echo "all $pass suites pass"
else
  echo "$pass passed, $fail FAILED:$failed"
  exit 1
fi
