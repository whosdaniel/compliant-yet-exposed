"""pilot2j_wsweep.py -- does patient observation (larger W) rescue the stressed regime?

Tests the low-and-slow hypothesis: at the compounded-stress operating
point (cross-pool corr 0.5, within-pool gamma 0.5, K=5), sweep the observation budget
W = 4..128 and see whether chance-adjusted recovery (ARI) and per-realization significance rise
with W (a patient attacker eventually wins) or stay pinned near the permutation-null floor (the
stress regime is genuinely weak no matter how long you watch). Either answer is publishable and
honest. Reuses the analyze() harness from pilot2i (ARI + permutation null + pairwise-F1).
"""
from __future__ import annotations
import json, os
from pilot2i_metrics import analyze
from pilot2e_boundary import gen_joint

RES = os.path.join(os.path.dirname(__file__), "results")


def main():
    print("== W-sweep at stress (corr 0.5, gamma 0.5, K=5): does patience rescue recovery? ==")
    out = []
    for W in [4, 8, 16, 32, 64, 128]:
        r = analyze(lambda s, W=W: gen_joint(corr=0.5, gamma=0.5, W=W, K=5, M=30, seed=s), 5, f"stress W={W}")
        out.append({"W": W, **r})
    json.dump(out, open(os.path.join(RES, "pilot2j_wsweep.json"), "w"), indent=2)
    print(f"\nsaved -> {RES}/pilot2j_wsweep.json")
    print("-> if ARI climbs with W, the low-and-slow attack survives; if it stays ~0.1, the")
    print("   compounded-stress regime is genuinely weak regardless of observation budget.")


if __name__ == "__main__":
    main()
