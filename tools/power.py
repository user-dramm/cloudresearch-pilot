#!/usr/bin/env python3
"""
How likely is this study to detect a real improvement?

    python3 tools/power.py

Clause 2 needs pooled preference >= 65% AND a two-sided exact binomial p < .05.
Those two together set a hard vote threshold, and at small n the threshold is well
above 65% - at 35 completions it takes 24 wins, which is 68.6%.

Power is what that costs. If the new pipeline is genuinely much better the study will
say so; if it is only moderately better, the study can easily fail to notice. That is
worth knowing BEFORE the money is spent, because "NOT VALIDATED" would then mean
"we did not have the sample to tell", not "the pipeline is no better" - and those get
reported as the same thing if nobody worked this out in advance.

Standard library only.
"""
from math import comb


def binom_p_two(k, n):
    probs = [comb(n, i) / 2 ** n for i in range(n + 1)]
    return sum(p for p in probs if p <= probs[k] + 1e-12)


def threshold(n, min_pref=0.65, max_p=0.05):
    """Smallest number of wins satisfying both halves of clause 2."""
    return next((k for k in range(n + 1)
                 if k / n >= min_pref and binom_p_two(k, n) < max_p), None)


def power(n, k, true_p):
    return sum(comb(n, i) * true_p ** i * (1 - true_p) ** (n - i) for i in range(k, n + 1))


if __name__ == "__main__":
    print("=" * 78)
    print("POWER OF CLAUSE 2   (pooled preference >= 65% AND two-sided p < .05)")
    print("=" * 78)
    print("  n = completions that clear the quality gates, not participants launched.")
    print()
    print("  %-6s %-14s %s" % ("n", "wins needed", "chance clause 2 passes, by true preference"))
    print("  %-6s %-14s %s" % ("", "", "   70%      75%      80%      85%"))
    print("  " + "-" * 72)
    for n in (21, 28, 35, 42, 49):
        k = threshold(n)
        cells = "  ".join("%6.0f%%" % (power(n, k, p) * 100) for p in (0.70, 0.75, 0.80, 0.85))
        print("  %-6d %-14s %s" % (n, "%d (%.1f%%)" % (k, k / n * 100), cells))
    print()
    print("  Read it this way: at 35 completions a genuinely much better pipeline (80%)")
    print("  is detected 97% of the time, but a moderately better one (70%) is missed")
    print("  about a third of the time. If the result comes back NOT VALIDATED with a")
    print("  pooled preference in the 60s, the honest reading is 'underpowered', not")
    print("  'no better' - and the writeup should say so.")
