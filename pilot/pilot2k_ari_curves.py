"""pilot2k_ari_curves.py -- settle the question: do the correlation (8.4) and
within-pool gamma (8.7) sweeps keep their qualitative shape under the chance-corrected ARI, or
was their robustness an optimal-assignment-accuracy artifact (as at the SOC point, where raw
acc 0.45 collapsed to ARI 0.10)?

Re-runs the SAME operating points as the manuscript tables, now reporting ARI + pairwise-F1 +
permutation null (reusing pilot2i.analyze). c-sweep matches 8.4 (gamma=1, W=24, K=2); gamma-sweep
matches 8.7 (corr=0, W=24, K=2 and K=5).
"""
from __future__ import annotations
import json, os
from pilot2i_metrics import analyze
from pilot2e_boundary import gen_joint

RES = os.path.join(os.path.dirname(__file__), "results")


def main():
    out = {"c_sweep_g1_W24_K2": [], "gamma_sweep_corr0_W24": []}
    print("== c-sweep (gamma=1, W=24, K=2)  [matches 8.4 table] ==")
    for c in [0.0, 0.5, 0.9, 0.99, 1.0]:
        r = analyze(lambda s, c=c: gen_joint(corr=c, gamma=1.0, W=24, K=2, M=24, seed=s), 2, f"c={c}")
        out["c_sweep_g1_W24_K2"].append({"c": c, **r})
    print("== gamma-sweep (corr=0, W=24)  [matches 8.7 table] ==")
    for K, M in [(2, 24), (5, 30)]:
        for g in [1.0, 0.75, 0.5, 0.25, 0.0]:
            r = analyze(lambda s, g=g, K=K, M=M: gen_joint(corr=0.0, gamma=g, W=24, K=K, M=M, seed=s), K, f"g={g} K={K}")
            out["gamma_sweep_corr0_W24"].append({"K": K, "gamma": g, **r})
    json.dump(out, open(os.path.join(RES, "pilot2k_ari_curves.json"), "w"), indent=2)
    print(f"\nsaved -> {RES}/pilot2k_ari_curves.json")


if __name__ == "__main__":
    main()
