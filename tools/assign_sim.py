#!/usr/bin/env python3
"""
Does the balanced assignment in Code.gs actually work?

Reimplements assign_() faithfully - fewest-first over completed responses plus
pending assignments inside the 45-minute window - and compares it against the
per-browser random assignment it replaced. The README claims 91% of runs land
within one rater of even and that random leaves a pair at <=4 about 61% of the
time. Those numbers are worth checking rather than repeating.

Also measures what happens when the endpoint is flaky, because a failed assign
call silently falls back to a local hash.
"""
import random
from collections import Counter

PENDING_MIN = 45          # Code.gs PENDING_MINUTES
SESSION_MIN = 25          # a real session
ABANDON     = 0.20        # opens the link, never finishes
RUNS        = 4000


def simulate(pairs, n_raters, mode, fail_rate=0.0, rng=None):
    """Return the completed-response count per pair."""
    rng = rng or random
    done = Counter()                 # pair -> completed
    pending = []                     # (pair, arrival_minute, pid)
    arrivals = sorted(rng.uniform(0, 240) for _ in range(n_raters))

    for i, t in enumerate(arrivals):
        # expire stale pendings exactly as the cutoff does
        pending = [p for p in pending if t - p[1] < PENDING_MIN]

        if mode == "balanced" and rng.random() >= fail_rate:
            live = {p: done[p] + sum(1 for q in pending if q[0] == p) for p in pairs}
            lowest = min(live.values())
            pair = next(p for p in pairs if live[p] == lowest)   # first, as Code.gs does
        else:
            # per-browser: hash of the participant id, effectively uniform random
            pair = pairs[rng.randrange(len(pairs))]

        pending.append((pair, t, i))
        if rng.random() > ABANDON:
            done[pair] += 1

    return [done[p] for p in pairs]


def report(label, pairs, n, mode, fail_rate=0.0):
    rng = random.Random(20260805)
    even, smallest, spread = 0, [], []
    per_pair_min = 10 ** 9
    for _ in range(RUNS):
        counts = simulate(pairs, n, mode, fail_rate, rng)
        lo, hi = min(counts), max(counts)
        spread.append(hi - lo)
        smallest.append(lo)
        per_pair_min = min(per_pair_min, lo)
        if hi - lo <= 1:
            even += 1
    thin = sum(1 for s in smallest if s <= 4) / RUNS
    print("  %-34s within 1 of even %5.1f%%   mean smallest cell %4.1f   "
          "smallest pair <=4 in %5.1f%%   worst ever %d"
          % (label, even / RUNS * 100, sum(smallest) / RUNS, thin * 100, per_pair_min))


print("=" * 108)
print("ASSIGNMENT BALANCE  (%d simulated runs, %d%% abandonment, %d-min pending window)"
      % (RUNS, ABANDON * 100, PENDING_MIN))
print("=" * 108)

five = ["P1", "P2", "P3", "P4", "P5"]
three = ["P2", "P3", "P5"]

print("\nFIVE pairs, 35 raters launched")
report("per-browser random", five, 35, "random")
report("balanced endpoint", five, 35, "balanced")
report("balanced, endpoint fails 25%", five, 35, "balanced", 0.25)
report("balanced, with the 3x retry (~2%)", five, 35, "balanced", 0.016)

print("\nFIVE pairs, 44 launched to land ~35 completions")
report("balanced endpoint", five, 44, "balanced")
report("balanced, with the 3x retry (~2%)", five, 44, "balanced", 0.016)

print("\nTHREE pairs live (P1 and P4 not built), 44 launched")
report("balanced endpoint", three, 44, "balanced")

print("\n" + "=" * 108)
print("Note: CloudResearch only pays completions, so launching exactly 35 lands ~28.")
print("The 'mean smallest cell' column is the one that matters for clause 1 - a pair")
print("needs enough raters for 'new ahead' in it to mean anything.")
print("=" * 108)
