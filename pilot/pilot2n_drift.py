"""pilot2n_drift.py -- does the W=128 'patient observer' result survive non-stationarity, or is it
only stationary-IID sample-complexity? Three W-curves at the stressed regime (corr0.5, gamma0.5, K5):
  stationary    : labels + p/c/gamma fixed (= pilot2j upper bound)
  param_drift   : labels FIXED, but p/c/gamma drift slowly across windows
  churn         : labels CHANGE over time (DERs switch pools) + param drift
Ground truth = initial membership; churn should degrade recovery vs initial labels.
"""
from __future__ import annotations
import json, os
import numpy as np
from scipy.stats import norm
from pilot2_command_channel import _z, cluster, accuracy, SEEDS
from pilot2i_metrics import ari as _ari, pairwise_prf as _prf, perm_null as _perm

RES = os.path.join(os.path.dirname(__file__), "results")
NPERM = 200


def gen_drift(mode, K=5, M=30, W=128, p=0.5, corr=0.5, gamma=0.5, churn_rate=0.02, seed=0):
    rng = np.random.default_rng(seed)
    pools = np.array([i % K for i in range(M)]); rng.shuffle(pools)
    pools_true = pools.copy()
    active = np.zeros((M, W), dtype=bool)
    for w in range(W):
        if mode == "stationary":
            pw, cw, gw = p, corr, gamma
        else:
            pw = float(np.clip(p + rng.normal(0, 0.15), 0.05, 0.95))
            cw = float(np.clip(corr + rng.normal(0, 0.20), 0.0, 0.99))
            gw = float(np.clip(gamma + rng.normal(0, 0.20), 0.0, 1.0))
        if mode == "churn" and w > 0:
            for i in range(M):
                if rng.random() < churn_rate:
                    pools[i] = rng.integers(K)
        thr = norm.ppf(1.0 - pw)
        zsh = rng.standard_normal()
        pool_act = {k: (np.sqrt(cw) * zsh + np.sqrt(1.0 - cw) * rng.standard_normal()) > thr for k in range(K)}
        for i in range(M):
            base = pool_act[pools[i]]
            active[i, w] = base if (rng.random() < gw) else (rng.random() < pw)
    count = rng.poisson(np.clip(np.where(active, 900.0, 120.0), 1, None)).astype(float)
    size = np.where(active, 34.0, 300.0) + rng.normal(0, np.where(active, 4.0, 60.0))
    return np.hstack([_z(count), _z(size)]), pools_true


def analyze_drift(mode, W, K=5, M=30):
    oa, orr, of, p_ari, sig = [], [], [], [], []
    for s in range(SEEDS):
        feat, true = gen_drift(mode, K=K, M=M, W=W, seed=s)
        pred = cluster(feat, K)
        oa.append(accuracy(true, pred, K)); orr.append(_ari(true, pred)); of.append(_prf(true, pred)[2])
        rng = np.random.default_rng(20000 + s)
        na, nr = _perm(true, pred, K, rng, nperm=NPERM)
        pv = (np.sum(nr >= orr[-1]) + 1) / (NPERM + 1)
        p_ari.append(pv); sig.append(pv < 0.05)
    import numpy as _np
    return {"mode": mode, "W": W, "acc": round(float(_np.mean(oa)), 3),
            "ari": round(float(_np.mean(orr)), 3), "f1": round(float(_np.mean(of)), 3),
            "frac_sig": round(float(_np.mean(sig)), 2)}


def main():
    out = []
    for mode in ["stationary", "param_drift", "churn"]:
        print(f"== {mode} ==")
        for W in [8, 16, 32, 64, 128]:
            r = analyze_drift(mode, W)
            out.append(r)
            print(f"  W={W:>3}: acc={r['acc']:.3f} ari={r['ari']:.3f} f1={r['f1']:.3f} sig={r['frac_sig']:.2f}")
    json.dump(out, open(os.path.join(RES, "pilot2n_drift.json"), "w"), indent=2)
    print(f"\nsaved -> {RES}/pilot2n_drift.json")
    print("-> stationary rising = sample-complexity; if drift/churn plateaus, that is the real horizon.")


if __name__ == "__main__":
    main()
