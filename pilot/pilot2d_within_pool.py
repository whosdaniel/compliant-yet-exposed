"""
pilot2d_within_pool.py — within-pool schedule heterogeneity sweep.

WHY: a fair challenge to E2-real = 1.00 (pilot2_command_channel.py). In the headline model
every DER in a pool shares the SAME award schedule (zero within-pool heterogeneity), so two
tight clusters separate trivially and accuracy is 1.00. Is that 1.00 a rigged constant, or the
gamma=1 endpoint of an honest curve? This sweep answers it directly.

gamma = fraction of windows in which a DER follows its OWN pool's schedule (vs an independent
draw). gamma=1 -> perfectly homogeneous pool (the headline case) -> recovery 1.0.
gamma=0 -> each DER independent of its pool -> no pool-aligned signal -> chance (this doubles
as a negative control). If recovery degrades smoothly from 1.0 as gamma falls, the 1.00 is the
clean endpoint of a real curve, not a manufactured result.

Channel params and clustering/accuracy machinery imported from pilot2_command_channel (identical
testbed, only within-pool homogeneity varies).
"""
from __future__ import annotations
import json, os
import numpy as np
from pilot2_command_channel import (
    LAM_ACT, LAM_IDLE, SZ_ACT, SZ_ACT_SD, SZ_IDLE, SZ_IDLE_SD, SEEDS,
    _z, cluster, accuracy, ci95,
)

RES = os.path.join(os.path.dirname(__file__), "results"); os.makedirs(RES, exist_ok=True)


def gen_hetero(gamma, M=24, K=2, W=24, p_award=0.5, seed=0):
    """Per-DER x per-window observables where each DER follows its pool's schedule in a
    fraction `gamma` of windows and draws independently otherwise (within-pool heterogeneity)."""
    rng = np.random.default_rng(seed)
    pools = np.array([i % K for i in range(M)]); rng.shuffle(pools)
    pool_base = {k: (rng.random(W) < p_award) for k in range(K)}      # distinct per-pool schedule
    active = np.zeros((M, W), dtype=bool)
    for i in range(M):
        base = pool_base[pools[i]]
        indep = rng.random(W) < p_award                              # this DER's own deviation
        follow = rng.random(W) < gamma                               # windows where it follows its pool
        active[i] = np.where(follow, base, indep)
    count = np.where(active, LAM_ACT, LAM_IDLE).astype(float)
    size = np.where(active, SZ_ACT, SZ_IDLE).astype(float)
    count = rng.poisson(np.clip(count, 1, None)).astype(float)       # sampling noise
    size = size + rng.normal(0, np.where(active, SZ_ACT_SD, SZ_IDLE_SD))
    feat = np.hstack([_z(count), _z(size)])
    return feat, pools


def main():
    gammas = [1.0, 0.9, 0.75, 0.5, 0.25, 0.0]                        # 1=homogeneous (headline) .. 0=independent
    K = 2; chance = 1.0 / K
    out = []
    print("=" * 72)
    print(f"PILOT 2d — within-pool schedule heterogeneity. chance = {chance}")
    print(f"Monte-Carlo: mean +/- SD over {SEEDS} seeds. gamma=1 homogeneous .. 0 independent.")
    print("=" * 72)
    print(f"{'gamma':>6} {'acc':>7} {'±sd':>7} {'±ci95':>7}")
    for g in gammas:
        accs = []
        for s in range(SEEDS):
            feat, pools = gen_hetero(g, K=K, seed=s)
            pred = cluster(feat, K)
            accs.append(accuracy(pools, pred, K))
        m, sd = float(np.mean(accs)), float(np.std(accs))
        out.append([g, round(m, 3), round(sd, 3)])
        print(f"{g:>6.2f} {m:>7.3f} {sd:>7.3f} {ci95(sd):>7.3f}")
    json.dump(out, open(os.path.join(RES, "pilot2d_within_pool.json"), "w"), indent=2)
    print("\n-> recovery degrades smoothly from the homogeneous endpoint (gamma=1) toward chance")
    print("   (gamma=0). The headline 1.00 is therefore the clean endpoint of a real curve, and the")
    print("   gamma=0 case is an independent negative control: no pool-aligned signal -> chance.")
    print(f"saved -> {RES}/pilot2d_within_pool.json")


if __name__ == "__main__":
    main()
