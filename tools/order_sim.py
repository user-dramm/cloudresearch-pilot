#!/usr/bin/env python3
"""
Is the ORDER within a pair actually balanced, not just the pair counts?

Two separate fairness questions get confused with each other:

  1. Do the five pairs get roughly equal numbers of raters?  -> tools/assign_sim.py
  2. Within a pair, do roughly half the raters see version A first?  -> this file

Question 2 matters because seeing a video first is not neutral. The first is judged
in a vacuum; the second is judged against the first. If one version were shown first
more often than the other, part of the measured preference would be position rather
than quality - and the criterion cannot tell those apart. analysis.py reports the
position effect for exactly this reason.

MECHANISM. Code.gs returns `nth` = how many raters that pair already had. The form
uses nth % 2 to decide which version goes first (index.html setPair). So order
alternates as a pair fills: 0 -> A first, 1 -> B first, 2 -> A first.

THE WEAKNESS BEING MEASURED. `nth` counts completed responses plus assignments still
inside the 45-minute pending window. Someone who takes a slot and abandons stops
being counted once their assignment expires, so the next rater can be handed the
SAME nth - and therefore the same order - twice. This simulates that.
"""
import random
from collections import Counter

PENDING_MIN = 45
ABANDON     = 0.20
RUNS        = 4000
PAIRS       = ["P1", "P2", "P3", "P4", "P5"]


def run(n_launched, abandon, rng, fail_rate=0.0):
    """-> {pair: [A-first completions, B-first completions]}

    Mirrors assign_() in Code.gs closely, including the detail that a pending
    assignment is counted ONLY while that participant has not completed
    (`!done[apid]`). An earlier version of this counted every pending row inside
    the window, so a participant who had already finished was counted twice - once
    as a response and once as a pending slot. That inflated the counts, shifted
    every `nth`, and produced a 57-60%% order bias that did not exist.
    """
    done_by_pair = Counter()               # pair -> completed responses
    completed = set()                      # pids that finished
    first = {p: [0, 0] for p in PAIRS}
    pending = []                           # (pair, t, pid)
    arrivals = sorted(rng.uniform(0, 240) for _ in range(n_launched))

    for i, t in enumerate(arrivals):
        pending = [q for q in pending if t - q[1] < PENDING_MIN]

        if rng.random() < fail_rate:
            # endpoint unreachable: local hash decides both pair and order
            pair = PAIRS[rng.randrange(len(PAIRS))]
            nth = rng.randrange(2)
        else:
            live = {}
            for p in PAIRS:
                held = sum(1 for q in pending if q[0] == p and q[2] not in completed)
                live[p] = done_by_pair[p] + held
            lowest = min(live.values())
            pair = next(p for p in PAIRS if live[p] == lowest)
            nth = live[pair]

        pending.append((pair, t, i))
        if rng.random() > abandon:
            done_by_pair[pair] += 1
            completed.add(i)
            first[pair][nth % 2] += 1
    return first


def report(label, n, abandon, fail_rate=0.0):
    rng = random.Random(20260805)
    worst_skew, skews, pooled = 0.0, [], [0, 0]
    for _ in range(RUNS):
        first = run(n, abandon, rng, fail_rate)
        for p, (a, b) in first.items():
            tot = a + b
            if tot:
                skew = abs(a - b) / tot
                skews.append(skew)
                worst_skew = max(worst_skew, skew)
            pooled[0] += a
            pooled[1] += b
    tot = sum(pooled)
    print("  %-38s pooled A-first %.1f%%   mean within-pair skew %.1f%%   worst %.0f%%"
          % (label, pooled[0] / tot * 100, sum(skews) / len(skews) * 100, worst_skew * 100))


print("=" * 104)
print("ORDER BALANCE WITHIN A PAIR  (%d runs)" % RUNS)
print("=" * 104)
print("  'pooled A-first' should sit near 50%. 'skew' is how lopsided a single pair")
print("  gets: 0% is a perfect split, 100% means every rater in that pair saw the")
print("  same version first.")
print()
report("44 launched, 20% abandon", 44, 0.20)
report("44 launched, 0% abandon", 44, 0.00)
report("44 launched, 40% abandon", 44, 0.40)
report("44 launched, endpoint fails 25%", 44, 0.20, 0.25)
report("44 launched, with the 3x retry (~2%)", 44, 0.20, 0.016)
report("35 launched, 20% abandon", 35, 0.20)
print()
print("  A small pair is lopsided by arithmetic, not bias: 7 raters cannot split evenly,")
print("  so the floor for a 7-rater pair is 1/7 = 14%. Read the pooled figure for bias")
print("  and the skew for how much noise a single pair carries.")
