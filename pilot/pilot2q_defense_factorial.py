"""
pilot2q_defense_factorial.py — close the claim-evidence gap on the DEFENSE.

WHY: the manuscript (§8.2/§9) asserts "constant cadence + fixed-size padding; both are
required; either alone fails / demonstrably insufficient." But the original E3 defense sweep
(pilot2_command_channel.py) only tested the COMBINED `pad` condition — it never measured
cadence-alone or padding-alone separately. So "either alone fails" was reasoned, not measured.

This script measures it: a factorial of {no defense, padding-only, cadence-only, both} x
{count-only, size-only, count+size attacker} x {downlink-only model, bidirectional model}.

INTEGRITY (repo rule #1 — never tune to a desired result):
  - report ARI + permutation-null 97.5th pct, mean over 50 seeds, for EVERY cell.
  - whatever comes out stands. If cadence-alone closes the downlink channel, then "both
    required" is wrong for the primary channel and the manuscript must say so.

CRITICAL design point: what is the IDLE downlink packet?
  The primary feature is the per-window DOWNLINK command count. The large ~300 B record is
  UPLINK telemetry; using it as the "idle downlink size" silently imports the bidirectional
  channel. So we run TWO transparent size models and report both:
    - "downlink": idle downlink = small same-size keepalive/update (~34 B, ~setpoint size)
                  => downlink size is ~constant; only COUNT varies with activity.
    - "bidir":    the observer also sees the larger idle uplink telemetry (~300 B)
                  => size ALSO varies with activity (34 B active vs 300 B idle).
  size-only is measured with the ORIGINAL active/idle size contrast intact (not the
  "contrast-removed" control), so it is a real test of whether size independently leaks.
"""
from __future__ import annotations
import json, os
import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist
from scipy.optimize import linear_sum_assignment

RES = os.path.join(os.path.dirname(__file__), "results"); os.makedirs(RES, exist_ok=True)

# real-grounded params (identical to pilot2_command_channel.py)
LAM_ACT = 900.0       # downlink setpoints/hr, active (~4 s cadence)
LAM_IDLE_DL = 120.0   # downlink keepalive/update-on-change when idle (sparse)
SZ_CTRL, SZ_CTRL_SD = 34.0, 4.0       # downlink control record ~34 B (Modbus 12 + TLS 22) [measured]
SZ_TELEM, SZ_TELEM_SD = 300.0, 60.0   # UPLINK telemetry ~300 B [measured range]
SEEDS = 50
NPERM = 200


def _z(x):
    m = x.mean(1, keepdims=True); s = x.std(1, keepdims=True); s[s == 0] = 1
    return (x - m) / s


def cluster(feat, K):
    return fcluster(linkage(pdist(feat, "euclidean"), "ward"), K, "maxclust")


def ari(true, pred):
    n = len(true); a = np.unique(true); b = np.unique(pred)
    cont = np.array([[np.sum((true == i) & (pred == j)) for j in b] for i in a], dtype=float)
    sa = cont.sum(1); sb = cont.sum(0)
    idx = np.sum([v * (v - 1) / 2 for v in cont.flatten()])
    ea = np.sum([v * (v - 1) / 2 for v in sa]); eb = np.sum([v * (v - 1) / 2 for v in sb])
    tot = n * (n - 1) / 2
    exp = ea * eb / tot if tot else 0.0; mx = (ea + eb) / 2
    return (idx - exp) / (mx - exp) if mx != exp else 0.0


def gen(size_model, defense, M=24, K=2, W=24, p=0.5, seed=0):
    """Per-DER x per-window (count, size). defense shapes the observable downlink stream."""
    rng = np.random.default_rng(seed)
    pools = np.array([i % K for i in range(M)]); rng.shuffle(pools)
    pool_sched = {k: (rng.random(W) < p) for k in range(K)}
    active = np.array([pool_sched[pools[i]] for i in range(M)])

    # ---- count: activity-dependent unless cadence-equalized ----
    if defense in ("cadence", "both"):
        rate = np.full((M, W), (LAM_ACT + LAM_IDLE_DL) / 2.0)   # constant cadence, no activity dependence
    else:
        rate = np.where(active, LAM_ACT, LAM_IDLE_DL).astype(float)
    count = rng.poisson(np.clip(rate, 1, None)).astype(float)

    # ---- size: model-dependent, then padding-equalized if defended ----
    if defense in ("padding", "both"):
        size = np.full((M, W), SZ_CTRL) + rng.normal(0, SZ_CTRL_SD, (M, W))   # fixed-size padding
    else:
        if size_model == "downlink":
            # idle downlink = small same-size keepalive (~setpoint). size ~ constant (only count varies).
            size = np.full((M, W), SZ_CTRL) + rng.normal(0, SZ_CTRL_SD, (M, W))
        elif size_model == "bidir":
            # observer also sees larger idle uplink telemetry -> size varies active(34)/idle(300).
            size = np.where(active, SZ_CTRL, SZ_TELEM).astype(float)
            size = size + rng.normal(0, np.where(active, SZ_CTRL_SD, SZ_TELEM_SD))
        else:
            raise ValueError(size_model)
    return count, size, pools


FEATURES = {
    "count_only": lambda c, s: _z(c),
    "size_only":  lambda c, s: _z(s),
    "joint":      lambda c, s: np.hstack([_z(c), _z(s)]),
}


def cell(size_model, defense, feat_name, K=2, W=24, p=0.5, seeds=SEEDS):
    feat_fn = FEATURES[feat_name]
    aris, null = [], []
    for s in range(seeds):
        c, sz, pools = gen(size_model, defense, K=K, W=W, p=p, seed=s)
        pred = cluster(feat_fn(c, sz), K)
        aris.append(ari(pools, pred))
        rng = np.random.default_rng(9000 + s)
        for _ in range(NPERM // seeds + 1):
            null.append(ari(rng.permutation(pools), pred))
    return float(np.mean(aris)), float(np.std(aris)), float(np.percentile(null, 97.5))


def main():
    corners = [
        ("favorable (K=2, W=24)", dict(K=2, W=24, p=0.5)),
        ("mild stress (K=5, W=32)", dict(K=5, W=32, p=0.5)),
    ]
    defenses = ["none", "padding", "cadence", "both"]
    out = {"n_seeds": SEEDS, "nperm": NPERM, "params": dict(
        LAM_ACT=LAM_ACT, LAM_IDLE_DL=LAM_IDLE_DL, SZ_CTRL=SZ_CTRL, SZ_TELEM=SZ_TELEM), "cells": {}}

    for size_model in ("downlink", "bidir"):
        print("=" * 92)
        print(f"SIZE MODEL = {size_model}   "
              + ("(idle downlink = small keepalive ~34B; only COUNT varies)" if size_model == "downlink"
                 else "(observer also sees idle uplink telemetry ~300B; SIZE also varies)"))
        print("=" * 92)
        for cname, ckw in corners:
            print(f"\n  corner: {cname}   [null ARI ~ 0; 97.5%-null in brackets]")
            print(f"    {'defense':10s} | {'count_only':>18s} | {'size_only':>18s} | {'joint':>18s}")
            print("    " + "-" * 74)
            for dfn in defenses:
                cells = {}
                line = f"    {dfn:10s} |"
                for fn in ("count_only", "size_only", "joint"):
                    m, sd, nq = cell(size_model, dfn, fn, **ckw)
                    cells[fn] = dict(ari=round(m, 3), sd=round(sd, 3), null975=round(nq, 3))
                    line += f" {m:5.2f}±{sd:4.2f}[{nq:4.2f}] |"
                out["cells"][f"{size_model}|{cname}|{dfn}"] = cells
                print(line)
        print()

    # ---- verdict (read straight off the numbers) ----
    def closed(model, corner, dfn):
        c = out["cells"][f"{model}|{corner}|{dfn}"]
        return all(c[f]["ari"] <= max(0.15, c[f]["null975"] + 0.05) for f in c)  # all attackers at/below null
    fav = "favorable (K=2, W=24)"
    print("=" * 92); print("VERDICT (does the defense drive ALL THREE attackers to the null?)"); print("=" * 92)
    for model in ("downlink", "bidir"):
        print(f"  [{model}]  cadence-alone closes = {closed(model, fav, 'cadence')} ; "
              f"padding-alone closes = {closed(model, fav, 'padding')} ; both closes = {closed(model, fav, 'both')}")
    out["verdict_favorable"] = {m: {d: closed(m, fav, d) for d in ("padding", "cadence", "both")}
                                for m in ("downlink", "bidir")}
    with open(os.path.join(RES, "pilot2q_defense_factorial.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nsaved -> {RES}/pilot2q_defense_factorial.json")


if __name__ == "__main__":
    main()
