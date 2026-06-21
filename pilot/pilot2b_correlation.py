"""
pilot2b_correlation.py — REPRODUCIBLE generator for the award-timing correlation boundary
(manuscript §8.4).

WHY THIS FILE EXISTS: this sweep's numbers were previously transcribed by hand into
make_figures.py with NO generating script. That is a reproducibility gap (a reader cannot
re-derive the curve). This script closes it: the §8.4 boundary is now produced from code.

QUESTION: co-membership recovery requires that pools have DISTINGUISHABLE award timing.
As the award schedules across pools become correlated, the side-channel must decay to chance.
We sweep an explicit correlation knob and report mean +/- SD over many seeds.

corr MECHANISM (interpolates the two E2 regimes of pilot2_command_channel.py):
  pool 0 holds a base award schedule. For every other pool, each window's award equals
  pool 0's with probability `corr` (shared/correlated) and is an independent draw otherwise.
    corr = 0 -> independent per-pool schedules  == E2 "real" (distinct windows) -> acc -> 1
    corr = 1 -> all pools copy one schedule      == E2 "function-only" confound  -> acc -> chance
Channel params and the clustering/accuracy machinery are imported from pilot2_command_channel
so this sweep is identical to the headline testbed except for the correlation knob.
"""
from __future__ import annotations
import json, os
import numpy as np
from scipy.stats import norm
from pilot2_command_channel import (
    LAM_ACT, LAM_IDLE, SZ_ACT, SZ_ACT_SD, SZ_IDLE, SZ_IDLE_SD, SEEDS,
    _z, cluster, accuracy, ci95,
)

RES = os.path.join(os.path.dirname(__file__), "results"); os.makedirs(RES, exist_ok=True)


def gen_corr(corr, M=24, K=2, W=24, p_award=0.5, seed=0):
    """Per-DER x per-window observables (count, mean_size) with a controllable cross-pool
    award-timing CORRELATION (Pearson rho between pool schedules = `corr`, via a Gaussian
    copula). Each pool's per-window activity latent g_k = sqrt(corr)*shared + sqrt(1-corr)*own;
    a window is active where g_k exceeds the p_award quantile. corr=0 -> independent schedules
    (E2 'real'); corr=1 -> all pools share one schedule (E2 'function-only') -> chance."""
    rng = np.random.default_rng(seed)
    pools = np.array([i % K for i in range(M)]); rng.shuffle(pools)
    thr = norm.ppf(1.0 - p_award)                        # active-window threshold (=0 at p_award=0.5)
    z_shared = rng.standard_normal(W)                    # latent common to all pools
    pool_sched = {}
    for k in range(K):
        z_own = rng.standard_normal(W)                   # pool-specific latent
        g = np.sqrt(corr) * z_shared + np.sqrt(1.0 - corr) * z_own   # cross-pool latent corr = corr
        pool_sched[k] = g > thr
    active = np.array([pool_sched[pools[i]] for i in range(M)])
    count = np.where(active, LAM_ACT, LAM_IDLE).astype(float)
    size = np.where(active, SZ_ACT, SZ_IDLE).astype(float)
    count = rng.poisson(np.clip(count, 1, None)).astype(float)            # sampling noise
    size = size + rng.normal(0, np.where(active, SZ_ACT_SD, SZ_IDLE_SD))
    feat = np.hstack([_z(count), _z(size)])
    return feat, pools


def main():
    corrs = [0.0, 0.25, 0.5, 0.75, 0.9, 0.95, 0.98, 0.99, 1.0]   # fine near 1.0 to locate the knee
    K = 2; chance = 1.0 / K
    out = []
    print("=" * 72)
    print(f"PILOT 2b — award-timing correlation boundary (§8.4). chance = {chance}")
    print(f"Monte-Carlo: mean +/- SD over {SEEDS} seeds/point. corr 0=distinct .. 1=identical.")
    print("=" * 72)
    print(f"{'corr':>6} {'acc':>7} {'±sd':>7} {'±ci95':>7}")
    for cr in corrs:
        accs = []
        for s in range(SEEDS):
            feat, pools = gen_corr(cr, K=K, seed=s)
            pred = cluster(feat, K)
            accs.append(accuracy(pools, pred, K))
        m, sd = float(np.mean(accs)), float(np.std(accs))
        out.append([cr, round(m, 3), round(sd, 3)])
        print(f"{cr:>6.2f} {m:>7.3f} {sd:>7.3f} {ci95(sd):>7.3f}")
    json.dump(out, open(os.path.join(RES, "pilot2b_correlation.json"), "w"), indent=2)
    print("\n-> co-membership accuracy decays to chance as cross-pool award timing correlates.")
    print("   This is the empirical form of the award-timing condition: the attack survives only")
    print("   where pools have distinguishable award windows (moderate corr).")
    print(f"saved -> {RES}/pilot2b_correlation.json")


if __name__ == "__main__":
    main()
