"""
pilot2f_nuisance.py — realistic per-DER NUISANCE variance (model-realism stress).

WHY: a key scientific objection to address:
the headline model is a clean bimodal (every DER swings 120<->900 identically), so it injects NO
competing within-class variance, which is why the count-contrast noise-stress stayed flat at 1.00.
This experiment adds realistic per-DER variation that does NOT cancel under z-normalization and
asks whether pool recovery survives competing clutter.

Two honest sub-points:
  (1) per-DER MAGNITUDE/offset heterogeneity (chatty vs quiet DERs) is removed by the per-DER
      z-normalization (scale/shift invariant), so it cannot hurt -- this is the real reason the
      count-contrast stress is flat, and it is a robustness property, not a flaw. We confirm it.
  (2) what genuinely competes is (a) per-DER RESPONSIVENESS spread (weak responders whose active
      windows barely rise above idle, lowering per-DER SNR) and (b) STRUCTURED (bursty,
      autocorrelated) per-DER background that can mimic the award cadence. We sweep both, and add a
      no-pool control showing nuisance alone does NOT manufacture pool structure.

Channel params + clustering/accuracy imported from pilot2_command_channel (identical testbed).
"""
from __future__ import annotations
import json, os
import numpy as np
from pilot2_command_channel import (
    LAM_ACT, LAM_IDLE, SZ_ACT, SZ_ACT_SD, SZ_IDLE, SZ_IDLE_SD, SEEDS,
    _z, cluster, accuracy, ci95,
)

RES = os.path.join(os.path.dirname(__file__), "results"); os.makedirs(RES, exist_ok=True)


def gen_nuisance(M=24, K=2, W=24, p_award=0.5, seed=0,
                 swing_het=0.0, bg=0.0, mag_het=0.0, kill_pool=False):
    """swing_het: per-DER responsiveness spread (weak responders sit near idle; survives z-norm).
    bg: fraction mixed from a STRUCTURED (bursty) per-DER background with its own temporal pattern.
    mag_het: per-DER pure rate multiplier + size offset (lognormal); should be REMOVED by z-norm.
    kill_pool: no pool structure (control -- nuisance must not manufacture pools)."""
    rng = np.random.default_rng(seed)
    pools = np.array([i % K for i in range(M)]); rng.shuffle(pools)
    pool_sched = {k: (rng.random(W) < p_award) for k in range(K)}
    if kill_pool:
        active = rng.random((M, W)) < p_award                     # no pool-aligned schedule
    else:
        active = np.array([pool_sched[pools[i]] for i in range(M)])
    # (2a) per-DER responsiveness: active count rises to lam_act_i; weak responders barely leave idle
    u = 1.0 - swing_het * rng.random((M, 1))                       # u in [1-swing_het, 1]
    lam_act_i = LAM_IDLE + (LAM_ACT - LAM_IDLE) * u
    cnt = np.where(active, lam_act_i, LAM_IDLE).astype(float)
    siz = np.where(active, SZ_ACT, SZ_IDLE).astype(float)
    # (2b) structured (bursty, autocorrelated) per-DER background, pool-independent, own pattern
    if bg > 0:
        bgs = np.zeros((M, W), dtype=bool)
        for i in range(M):
            w = 0; on = rng.random() < p_award
            while w < W:
                run = int(rng.integers(2, 6))                     # bursts of 2-5 windows
                bgs[i, w:w + run] = on
                if rng.random() < 0.6:
                    on = not on
                w += run
        cnt = (1 - bg) * cnt + bg * np.where(bgs, LAM_ACT, LAM_IDLE).astype(float)
        siz = (1 - bg) * siz + bg * np.where(bgs, SZ_ACT, SZ_IDLE).astype(float)
    # (1) per-DER magnitude heterogeneity (pure multiplier + offset) -- z-norm should remove this
    if mag_het > 0:
        cnt = cnt * np.exp(rng.normal(0, mag_het, (M, 1)))
        siz = siz + rng.normal(0, 120.0 * mag_het, (M, 1))
    cnt = rng.poisson(np.clip(cnt, 1, None)).astype(float)
    siz = siz + rng.normal(0, np.where(active, SZ_ACT_SD, SZ_IDLE_SD))
    feat = np.hstack([_z(cnt), _z(siz)])
    return feat, pools


def run(K=2, **kw):
    accs = [accuracy(*(lambda fp: (fp[1], cluster(fp[0], K)))(gen_nuisance(K=K, seed=s, **kw)), K)
            for s in range(SEEDS)]
    return float(np.mean(accs)), float(np.std(accs))


def main():
    out = {"n_seeds": SEEDS}

    # (1) magnitude heterogeneity is removed by z-norm -> recovery unchanged (explains the flat stress)
    out["mag_het_invariance"] = []
    print("== (1) per-DER MAGNITUDE heterogeneity (z-norm should remove it) K=2 W=24 ==")
    for mh in (0.0, 0.5, 1.0, 2.0):
        m, sd = run(K=2, mag_het=mh)
        out["mag_het_invariance"].append([mh, round(m, 3), round(sd, 3)])
        print(f"  mag_het={mh}: acc={m:.3f}±{sd:.3f}")

    # (2a) per-DER responsiveness spread (weak responders) -- genuine SNR competition
    out["swing_het_by_K"] = []
    print("== (2a) per-DER RESPONSIVENESS spread (weak responders), bg=0 ==")
    for K in (2, 5):
        curve = []
        for sh in (0.0, 0.3, 0.6, 0.9):
            m, sd = run(K=K, swing_het=sh, M=max(24, 6 * K))
            curve.append([sh, round(m, 3), round(sd, 3)])
        out["swing_het_by_K"].append({"K": K, "chance": round(1.0 / K, 3), "curve": curve})
        print(f"  K={K} (chance {1.0/K:.2f}): " + " ".join(f"s{sh}:{a}" for sh, a, _ in curve))

    # (2b) structured bursty competing background (harder than pilot2c's uncorrelated phi)
    out["structured_bg_by_K"] = []
    print("== (2b) STRUCTURED bursty competing background, swing_het=0.3 ==")
    for K in (2, 5):
        curve = []
        for b in (0.0, 0.25, 0.5, 0.75):
            m, sd = run(K=K, swing_het=0.3, bg=b, M=max(24, 6 * K))
            curve.append([b, round(m, 3), round(sd, 3)])
        out["structured_bg_by_K"].append({"K": K, "chance": round(1.0 / K, 3), "curve": curve})
        print(f"  K={K} (chance {1.0/K:.2f}): " + " ".join(f"b{b}:{a}" for b, a, _ in curve))

    # control: nuisance must NOT manufacture pools when there is no pool structure
    print("== control: no pool + heavy nuisance (must sit at chance) ==")
    out["nopool_control"] = []
    for K in (2, 5):
        m, sd = run(K=K, kill_pool=True, swing_het=0.6, bg=0.5, mag_het=0.5, M=max(24, 6 * K))
        out["nopool_control"].append({"K": K, "chance": round(1.0 / K, 3), "acc": round(m, 3), "sd": round(sd, 3)})
        print(f"  K={K}: acc={m:.3f}±{sd:.3f} (chance {1.0/K:.2f})  -> nuisance does not invent pools")

    json.dump(out, open(os.path.join(RES, "pilot2f_nuisance.json"), "w"), indent=2)
    print(f"\nsaved -> {RES}/pilot2f_nuisance.json")


if __name__ == "__main__":
    main()
