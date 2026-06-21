"""
pilot2e_boundary.py — consolidated BOUNDARY characterization (committed + JSON-saving).

WHY: the magnitude needs to be
reported as a BOUNDARY across all knobs, not the favorable corner. The independent re-audit had
explored this in scratch scripts (adversarial_audit*.py) that only printed to stdout; this file
supersedes them with a single reproducible generator that SAVES JSON, so figures and prose read
from committed data (never hand-typed -- the lesson of the correlation-sweep gap).

gen_joint UNIFIES the two single-knob generators: cross-pool award correlation (Gaussian copula,
as pilot2b) AND within-pool schedule heterogeneity gamma (as pilot2d). corr=0, gamma=1 reproduces
the headline E2-real. All channel params and the clustering/accuracy machinery are imported from
pilot2_command_channel, so only the parameters differ.

Outputs (results/pilot2e_boundary.json), each mean +/- SD over SEEDS seeds:
  gamma_by_K   : within-pool heterogeneity curve at K = 2, 3, 5      (the omitted boundary knob)
  corr_by_W    : cross-pool correlation curve at several (K, W)       (the knee moves with W)
  joint        : named joint operating points (knobs compounded, not one-at-a-time)
  e6_floor_by_K: no-structure negative-control floor as K grows       (optimal-assignment baseline)
  noise_stress : recovery as the active/idle count contrast shrinks   (count-channel saturation)
"""
from __future__ import annotations
import json, os
import numpy as np
from scipy.stats import norm
from pilot2_command_channel import (
    LAM_ACT, LAM_IDLE, SZ_ACT, SZ_ACT_SD, SZ_IDLE, SZ_IDLE_SD, SEEDS,
    _z, cluster, accuracy, gen, ci95,
)

RES = os.path.join(os.path.dirname(__file__), "results"); os.makedirs(RES, exist_ok=True)


def gen_joint(corr=0.0, gamma=1.0, M=24, K=2, W=24, p_award=0.5, seed=0,
              lam_act=LAM_ACT, lam_idle=LAM_IDLE, sz_act=SZ_ACT):
    """Unified generator: cross-pool award correlation (copula) + within-pool heterogeneity gamma.
    corr=0, gamma=1 == headline E2-real (distinct, perfectly-synchronized pools)."""
    rng = np.random.default_rng(seed)
    pools = np.array([i % K for i in range(M)]); rng.shuffle(pools)
    thr = norm.ppf(1.0 - p_award)
    z_shared = rng.standard_normal(W)
    pool_sched = {}
    for k in range(K):
        z_own = rng.standard_normal(W)
        g = np.sqrt(corr) * z_shared + np.sqrt(1.0 - corr) * z_own   # cross-pool latent corr = corr
        pool_sched[k] = g > thr
    active = np.zeros((M, W), dtype=bool)
    for i in range(M):
        base = pool_sched[pools[i]]
        indep = rng.random(W) < p_award
        follow = rng.random(W) < gamma                               # within-pool homogeneity
        active[i] = np.where(follow, base, indep)
    count = np.where(active, lam_act, lam_idle).astype(float)
    size = np.where(active, sz_act, SZ_IDLE).astype(float)
    count = rng.poisson(np.clip(count, 1, None)).astype(float)
    size = size + rng.normal(0, np.where(active, SZ_ACT_SD, SZ_IDLE_SD))
    feat = np.hstack([_z(count), _z(size)])
    return feat, pools


def run_joint(K=2, **kw):
    accs = [accuracy(*(lambda fp: (fp[1], cluster(fp[0], K)))(gen_joint(K=K, seed=s, **kw)), K)
            for s in range(SEEDS)]
    return float(np.mean(accs)), float(np.std(accs))


def main():
    out = {"n_seeds": SEEDS}

    # within-pool heterogeneity (gamma) at K = 2, 3, 5  -- the boundary knob omitted from the draft
    gammas = [1.0, 0.9, 0.75, 0.5, 0.25, 0.0]
    out["gamma_by_K"] = []
    print("== gamma_by_K (within-pool homogeneity; corr=0) ==")
    for K in (2, 3, 5):
        curve = []
        for g in gammas:
            m, sd = run_joint(K=K, gamma=g, M=max(24, 6 * K))
            curve.append([g, round(m, 3), round(sd, 3)])
        out["gamma_by_K"].append({"K": K, "chance": round(1.0 / K, 3), "curve": curve})
        print(f"  K={K} (chance {1.0/K:.2f}): " + " ".join(f"g{g}:{a}" for g, a, _ in curve))

    # cross-pool correlation at several (K, W) -- the knee moves to lower corr at small W
    corrs = [0.0, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0]
    out["corr_by_W"] = []
    print("== corr_by_W (cross-pool award correlation; gamma=1) ==")
    for K, W in [(2, 24), (2, 8), (2, 4), (5, 24), (5, 8)]:
        curve = []
        for c in corrs:
            m, sd = run_joint(K=K, W=W, corr=c, M=max(24, 6 * K))
            curve.append([c, round(m, 3), round(sd, 3)])
        out["corr_by_W"].append({"K": K, "W": W, "chance": round(1.0 / K, 3), "curve": curve})
        print(f"  K={K} W={W} (chance {1.0/K:.2f}): " + " ".join(f"c{c}:{a}" for c, a, _ in curve))

    # joint operating points -- the knobs compounded, not varied one-at-a-time
    out["joint"] = []
    print("== joint operating points (compounded knobs) ==")
    scen = [
        ("headline (corr0, gamma1, W24, K2)",       dict(corr=0.0,  gamma=1.0,  W=24, K=2, M=24)),
        ("mild (corr0.5, gamma0.75, W16, K2)",       dict(corr=0.5,  gamma=0.75, W=16, K=2, M=24)),
        ("mild K5 (corr0.5, gamma0.75, W16, K5)",    dict(corr=0.5,  gamma=0.75, W=16, K=5, M=30)),
        ("SOC-budget (corr0.5, gamma0.5, W8, K5)",   dict(corr=0.5,  gamma=0.5,  W=8,  K=5, M=30)),
        ("battery-real (corr0.75, gamma0.5, W8, K5)",dict(corr=0.75, gamma=0.5,  W=8,  K=5, M=30)),
        ("pessimistic (corr0.75, gamma0.5, W4, K5)", dict(corr=0.75, gamma=0.5,  W=4,  K=5, M=30)),
    ]
    for name, kw in scen:
        m, sd = run_joint(**kw); ch = 1.0 / kw["K"]
        out["joint"].append({"label": name, **{k: kw[k] for k in ("corr", "gamma", "W", "K", "M")},
                             "chance": round(ch, 3), "acc": round(m, 3), "sd": round(sd, 3)})
        print(f"  {name:<44} acc={m:.3f}±{sd:.3f} (chance {ch:.2f})")

    # negative-control floor as K grows (optimal-assignment baseline rises with K)
    out["e6_floor_by_K"] = []
    print("== e6_floor_by_K (no-structure negative control; optimal-assignment floor) ==")
    for K in (2, 3, 5, 8):
        accs = [accuracy(*(lambda fp: (fp[1], cluster(fp[0], K)))(gen(no_pools=True, K=K, seed=s, M=max(24, 6 * K))), K)
                for s in range(SEEDS)]
        m, sd = float(np.mean(accs)), float(np.std(accs)); ch = 1.0 / K
        out["e6_floor_by_K"].append({"K": K, "chance": round(ch, 3), "floor": round(m, 3),
                                     "sd": round(sd, 3), "excess_over_chance": round(m - ch, 3)})
        print(f"  K={K}: floor={m:.3f}±{sd:.3f} (chance {ch:.2f}, excess +{m-ch:.3f})")

    # count-channel saturation: shrink active/idle count contrast (best case otherwise)
    out["noise_stress"] = []
    print("== noise_stress (shrink active/idle count contrast; K2 W24 gamma1 corr0) ==")
    for la in (900, 480, 300, 200, 150):
        m, sd = run_joint(corr=0.0, gamma=1.0, W=24, K=2, lam_act=float(la))
        out["noise_stress"].append([la, round(la / 120.0, 2), round(m, 3), round(sd, 3)])
        print(f"  lam_act={la:>4} (ratio {la/120:.1f}x): acc={m:.3f}±{sd:.3f}")

    json.dump(out, open(os.path.join(RES, "pilot2e_boundary.json"), "w"), indent=2)
    print(f"\nsaved -> {RES}/pilot2e_boundary.json")
    print("-> magnitude is a BOUNDARY: near-perfect only at the favorable corner; cost scales steeply")
    print("   with within-pool heterogeneity, pool count, observation budget, and award correlation.")


if __name__ == "__main__":
    main()
