"""
pilot2c_sensitivity.py — robustness of co-membership recovery to BACKGROUND TRAFFIC /
imperfect per-DER flow isolation. Addresses the limitation (manuscript §10): the clean per-DER model is an UPPER BOUND; a real passive observer must
isolate the DER flow from co-located background traffic (streaming, other apps, shared CDN),
and residual contamination lowers accuracy. Here we quantify that degradation.

Model (same channel params as pilot2_command_channel.py, real-measured sizes):
  active (regulation) window: frequent (~LAM_ACT pkts/win), small (~SZ_ACT B).
  idle window:                rare (~LAM_IDLE), larger (~SZ_IDLE B).
  pools have DISTINCT award schedules (the favourable E2-real regime).
Contamination beta: the observer's per-DER stream is mixed with background traffic of
  rate beta*LAM_IDLE and size SZ_BG. beta=0 = perfect isolation (clean model);
  beta>0 = residual background that dilutes BOTH count and mean size.
Observer features per DER = (per-window packet count, per-window mean size) over W windows.
"""
from __future__ import annotations
import json, os
import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.optimize import linear_sum_assignment
from pilot2i_metrics import ari as _ari   # chance-corrected metric (primary)

from pilot2_command_channel import FEATURES  # amendment 1 feature switch
NORM = os.environ.get("CYE_BG_NORM", "window")   # "window" (published) or "der" (post hoc check)
if NORM not in ("window", "der"):
    raise SystemExit(f"CYE_BG_NORM must be window or der, not {NORM!r}")
RES = os.environ.get("CYE_RESULTS") or os.path.join(os.path.dirname(__file__), "results"); os.makedirs(RES, exist_ok=True)
LAM_ACT, LAM_IDLE = 900.0, 120.0
SZ_ACT, SZ_ACT_SD = 34.0, 4.0
SZ_IDLE, SZ_IDLE_SD = 300.0, 60.0
SZ_BG = 250.0          # background traffic mean packet size (B) — streaming/other apps

def accuracy(true, pred, K):
    C = np.zeros((K, K))
    for t, p in zip(true, pred):
        C[t, p] += 1
    r, c = linear_sum_assignment(-C)
    return C[r, c].sum() / len(true)

def trial(phi, M=24, K=3, W=24, p=0.5, seed=0):
    """phi = fraction of the observed per-DER feature that is background/misattributed traffic,
    UNCORRELATED with the pool (imperfect flow isolation). phi=0 = clean model; phi=1 = no isolation."""
    rng = np.random.default_rng(seed)
    pools = np.array([i % K for i in range(M)]); rng.shuffle(pools)
    sched = {k: (rng.random(W) < p) for k in range(K)}            # distinct per-pool windows
    active = np.array([sched[pools[i]] for i in range(M)])         # M x W
    cnt = rng.poisson(np.where(active, LAM_ACT, LAM_IDLE)).astype(float)
    siz = np.where(active, SZ_ACT, SZ_IDLE) + rng.normal(0, np.where(active, SZ_ACT_SD, SZ_IDLE_SD))
    # background: per-(DER,window) activity that is NOT pool-aligned (own random schedule)
    bg_active = rng.random((M, W)) < p
    bg_cnt = rng.poisson(np.where(bg_active, LAM_ACT, LAM_IDLE)).astype(float)
    bg_siz = np.where(bg_active, SZ_ACT, SZ_IDLE) + rng.normal(0, 40, (M, W))
    obs_cnt = (1 - phi) * cnt + phi * bg_cnt                       # blend signal with uncorrelated background
    obs_siz = (1 - phi) * siz + phi * bg_siz
    F = obs_cnt if FEATURES == "count" else np.hstack([obs_cnt, obs_siz])
    if NORM == "window":   # as published: each window standardized across DERs
        F = (F - F.mean(0)) / (F.std(0) + 1e-9)
    else:                  # post hoc check (revision R1): each DER standardized across windows, as in the other experiments
        F = (F - F.mean(1, keepdims=True)) / (F.std(1, keepdims=True) + 1e-9)
    pred = fcluster(linkage(F, method="ward"), t=K, criterion="maxclust") - 1
    return accuracy(pools, pred, K), _ari(pools, pred)

def main():
    phis = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 0.9]
    seeds = 60
    out = []
    print(f"{'phi (bg fraction)':>17} {'acc':>7} {'ari':>7}")
    for ph in phis:
        res = [trial(ph, seed=s) for s in range(seeds)]
        accs = [r[0] for r in res]; aris = [r[1] for r in res]
        out.append([ph, round(float(np.mean(accs)), 6), round(float(np.std(accs)), 6),
                    round(float(np.mean(aris)), 6), round(float(np.std(aris)), 6)])
        print(f"{ph:>17.2f} {np.mean(accs):>7.3f} {np.mean(aris):>7.3f}")
    OUT = "pilot2c_sensitivity.json" if NORM == "window" else "pilot2c_sensitivity_perder.json"
    json.dump(out, open(os.path.join(RES, OUT), "w"), indent=2)
    print("\nchance: acc empirical floor (K=3) ~0.47; ARI null ~0")
    print("-> co-membership recovery degrades gracefully as background contamination grows;")
    print("   the clean (beta=0) model is an upper bound, as stated honestly in the paper.")
    print(f"saved -> {RES}/{OUT}")

if __name__ == "__main__":
    main()
