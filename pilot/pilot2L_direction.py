"""pilot2L_direction.py -- DIRECTION ABLATION (is the leak command-DOWN, or generic
active/idle traffic-state classification usable from either direction?).

Models separate per-DER DOWNLINK command and UPLINK telemetry streams over the SAME award schedule
(corr/gamma as pilot2e), then runs ARI + permutation null on feature subsets:
  downlink (cmd count+size) / uplink (tel count+size) / bidirectional / downlink-count-only / uplink-count-only

Honest design: both per-DER directions are award-correlated in the model (telemetry, IF per-DER, is
also 4s during a regulation award per CAISO direct-telemetry). So the in-model question is narrow:
does the DOWNLINK command stream alone (and its COUNT alone, no sizes) recover co-membership? If yes,
the 'command-down' thesis stands for the per-DER observable. (Deployment note for the manuscript:
CAISO uplink telemetry is aggregate, not per-DER -- so downlink commands are the per-DER observable;
that is a stated architecture argument, not shown here.)
"""
from __future__ import annotations
import json, os
import numpy as np
from scipy.stats import norm
from pilot2_command_channel import _z, cluster, accuracy, SEEDS
from pilot2i_metrics import analyze

RES = os.path.join(os.path.dirname(__file__), "results")

CMD_ACT, CMD_IDLE = 900.0, 30.0    # downlink setpoints: many when awarded (~4s), ~none idle
TEL_ACT, TEL_IDLE = 900.0, 120.0   # uplink telemetry: 4s during award (CAISO), 30s baseline otherwise
SZ_CMD, SZ_TEL = 34.0, 341.0


def gen_dir(feature, K=2, M=24, W=24, p_award=0.5, corr=0.0, gamma=1.0, seed=0):
    rng = np.random.default_rng(seed)
    pools = np.array([i % K for i in range(M)]); rng.shuffle(pools)
    thr = norm.ppf(1.0 - p_award)
    z_shared = rng.standard_normal(W)
    pool_sched = {}
    for k in range(K):
        z_own = rng.standard_normal(W)
        g = np.sqrt(corr) * z_shared + np.sqrt(1.0 - corr) * z_own
        pool_sched[k] = g > thr
    active = np.zeros((M, W), dtype=bool)
    for i in range(M):
        base = pool_sched[pools[i]]
        indep = rng.random(W) < p_award
        follow = rng.random(W) < gamma
        active[i] = np.where(follow, base, indep)
    cmd = rng.poisson(np.clip(np.where(active, CMD_ACT, CMD_IDLE), 1, None)).astype(float)
    tel = rng.poisson(np.clip(np.where(active, TEL_ACT, TEL_IDLE), 1, None)).astype(float)
    cmd_sz = SZ_CMD + rng.normal(0, 4, (M, W))
    tel_sz = SZ_TEL + rng.normal(0, 60, (M, W))
    cols = {
        "downlink": [_z(cmd), _z(cmd_sz)],
        "uplink": [_z(tel), _z(tel_sz)],
        "bidir": [_z(cmd), _z(cmd_sz), _z(tel), _z(tel_sz)],
        "downlink_count_only": [_z(cmd)],
        "uplink_count_only": [_z(tel)],
    }[feature]
    return np.hstack(cols), pools


def main():
    feats = ["downlink", "uplink", "bidir", "downlink_count_only", "uplink_count_only"]
    conds = [("headline K2 (corr0,g1,W24)", dict(K=2, M=24, W=24, corr=0.0, gamma=1.0)),
             ("mild K5 (corr0.5,g0.75,W16)", dict(K=5, M=30, W=16, corr=0.5, gamma=0.75))]
    out = []
    for cname, kw in conds:
        print(f"== {cname} ==")
        for f in feats:
            r = analyze(lambda s, f=f, kw=kw: gen_dir(f, seed=s, **kw), kw["K"], f"{f:<20} {cname}")
            out.append({"cond": cname, "feature": f, **r})
    json.dump(out, open(os.path.join(RES, "pilot2L_direction.json"), "w"), indent=2)
    print(f"\nsaved -> {RES}/pilot2L_direction.json")
    print("-> key: does downlink_count_only recover (command-down thesis), and does uplink also carry it?")


if __name__ == "__main__":
    main()
