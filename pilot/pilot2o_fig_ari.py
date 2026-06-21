"""pilot2o_fig_ari.py -- ARI (chance-corrected) for the figure sweeps so the main figures can be
re-plotted in the primary metric: E2 controls (Fig 5), defenses (Fig 6), and the c-sweep at three
observation budgets (Fig 8). Lightweight: 50-seed ARI mean/SD, no permutation null (the null for ARI
is ~0 by construction). Saves results/pilot2o_fig_ari.json."""
from __future__ import annotations
import json, os
import numpy as np
from pilot2_command_channel import gen, cluster, accuracy, SEEDS
from pilot2i_metrics import ari, pairwise_prf
from pilot2e_boundary import gen_joint

RES = os.path.join(os.path.dirname(__file__), "results")


def curve(gen_fn, K, permute_label=False):
    a, r, f = [], [], []
    for s in range(SEEDS):
        feat, true = gen_fn(s)
        pred = cluster(feat, K)
        tgt = np.random.default_rng(900 + s).permutation(true) if permute_label else true
        a.append(accuracy(tgt, pred, K)); r.append(ari(tgt, pred)); f.append(pairwise_prf(tgt, pred)[2])
    return {"acc": round(float(np.mean(a)), 3), "ari": round(float(np.mean(r)), 3),
            "ari_sd": round(float(np.std(r)), 3), "f1": round(float(np.mean(f)), 3)}


def main():
    out = {}
    out["e2_controls"] = {
        "real": curve(lambda s: gen(seed=s), 2),
        "function_only": curve(lambda s: gen(same_windows=True, seed=s), 2),
        "random_label": curve(lambda s: gen(seed=s), 2, permute_label=True),
        "no_structure": curve(lambda s: gen(no_pools=True, seed=s), 2),
    }
    print("== E2 controls (ARI) ==")
    for k, v in out["e2_controls"].items():
        print(f"  {k:<16} acc={v['acc']:.3f} ari={v['ari']:.3f} f1={v['f1']:.3f}")

    out["defenses"] = {}
    for name, dp in [("jitter", 0.0), ("batch", 16.0), ("cover", 1.0), ("pad", 1.0), ("vpn", 1.0)]:
        out["defenses"][name] = curve(lambda s, name=name, dp=dp: gen(defense=name, dparam=dp, seed=s), 2)
    print("== defenses (ARI; pad/vpn should close to ~0, jitter/cover stay high) ==")
    for k, v in out["defenses"].items():
        print(f"  {k:<8} acc={v['acc']:.3f} ari={v['ari']:.3f}")

    out["c_multiW"] = []
    print("== c-sweep multi-W (ARI) ==")
    for W in [24, 8, 4]:
        for c in [0.0, 0.5, 0.9, 0.99, 1.0]:
            v = curve(lambda s, c=c, W=W: gen_joint(corr=c, gamma=1.0, W=W, K=2, M=24, seed=s), 2)
            out["c_multiW"].append({"W": W, "c": c, **v})
        row = [x for x in out["c_multiW"] if x["W"] == W]
        print(f"  W={W:>2}: " + " ".join(f"c{x['c']}:{x['ari']}" for x in row))

    json.dump(out, open(os.path.join(RES, "pilot2o_fig_ari.json"), "w"), indent=2)
    print(f"\nsaved -> {RES}/pilot2o_fig_ari.json")


if __name__ == "__main__":
    main()
