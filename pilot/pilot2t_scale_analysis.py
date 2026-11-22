"""
pilot2t_scale_analysis.py -- analysis of E8 (scale), revision R1, per revision/prereg_E7_E8.md.

Reads results/pilot2s_scale.jsonl (+ .json) written by pilot2s_scale.py and saves
results/pilot2t_scale_analysis.json, so the manuscript prose and fig_scale read committed numbers
(never hand-typed).

Reports fixed in the design file:
  ari_vs_M        : ARI (oracle, silK) at the smallest and largest M for every (cond, K, W)
  kw_at_largest_M : ARI over (K, W) at M = 12,288 (largest M with the full W grid) and at 49,152 (W 24/96)
  cost            : pdist + Ward wall-clock and worker peak RSS vs M, with log-log (O(M^2)) slope fits
Also derived from the same runs (descriptive, no new data):
  unknown_k       : silK minus oracle ARI, per condition and per W
EXPLORATORY (not in the design file; labeled as such wherever used):
  collision       : favorable condition, small W: how much of the ARI loss is explained by two pools
                    drawing the identical W-window award schedule (2^W possible schedules).
Run: python pilot2t_scale_analysis.py
"""
from __future__ import annotations
import json, os
import numpy as np
from scipy.stats import norm
from pilot2i_metrics import ari
from pilot2s_scale import workers_for

RES = os.environ.get("CYE_RESULTS") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def load():
    rows = [json.loads(l) for l in open(os.path.join(RES, "pilot2s_scale.jsonl")) if l.strip()]
    summ = json.load(open(os.path.join(RES, "pilot2s_scale.json")))
    return rows, summ["configs"]


def cell(configs, cond, K, W, M):
    hit = [c for c in configs if c["cond"] == cond and c["K"] == K and c["W"] == W and c["M"] == M]
    return hit[0] if hit else None


def ari_vs_M(configs):
    out = []
    for cond in ("favorable", "adverse"):
        for K in (2, 4, 8, 16, 32, 64):
            for W in (6, 12, 24, 48, 96):
                cs = sorted([c for c in configs if c["cond"] == cond and c["K"] == K and c["W"] == W],
                            key=lambda c: c["M"])
                if not cs:
                    continue
                lo, hi = cs[0], cs[-1]
                out.append({"cond": cond, "K": K, "W": W,
                            "M_min": lo["M"], "oracle_at_M_min": lo["ari_oracle"][0], "silK_at_M_min": lo["ari_silK"][0],
                            "M_max": hi["M"], "oracle_at_M_max": hi["ari_oracle"][0], "silK_at_M_max": hi["ari_silK"][0],
                            "n_at_M_max": hi["n"],
                            "oracle_delta": round(hi["ari_oracle"][0] - lo["ari_oracle"][0], 6),
                            "oracle_curve": [[c["M"], c["ari_oracle"][0], c["ari_oracle"][1]] for c in cs],
                            "silK_curve": [[c["M"], c["ari_silK"][0], c["ari_silK"][1]] for c in cs],
                            "khat_curve": [[c["M"], c["khat_mean"]] for c in cs]})
    return out


def kw_grid(configs, M):
    out = []
    for cond in ("favorable", "adverse"):
        for K in (2, 4, 8, 16, 32, 64):
            for W in (6, 12, 24, 48, 96):
                c = cell(configs, cond, K, W, M)
                if c:
                    out.append({"cond": cond, "K": K, "W": W, "n": c["n"],
                                "oracle": c["ari_oracle"], "silK": c["ari_silK"],
                                "khat_mean": c["khat_mean"], "khat_exact": c["khat_exact"]})
    return out


def cost(rows):
    tiers = []
    for M in sorted({r["M"] for r in rows}):
        rs = [r for r in rows if r["M"] == M]
        tt = np.array([r["t_tree"] for r in rs]); ts = np.array([r["t_sel"] for r in rs])
        tiers.append({"M": M, "runs": len(rs), "concurrent_workers": workers_for(M),
                      "t_tree_median_s": round(float(np.median(tt)), 6),
                      "t_tree_min_s": round(float(tt.min()), 6), "t_tree_max_s": round(float(tt.max()), 6),
                      "t_sel_median_s": round(float(np.median(ts)), 6),
                      "peak_rss_gb": round(float(max(r["rss_gb"] for r in rs)), 6),
                      "two_condensed_copies_gb": round(8.0 * M * (M - 1) / 1e9, 6)})
    M = np.array([t["M"] for t in tiers], float)
    tt = np.array([t["t_tree_median_s"] for t in tiers]); rss = np.array([t["peak_rss_gb"] for t in tiers])
    big = M >= 3072
    slope_t = float(np.polyfit(np.log(M[big]), np.log(tt[big]), 1)[0])
    slope_r_top = float(np.log(rss[-1] / rss[-2]) / np.log(M[-1] / M[-2]))
    nxt = int(M[-1] * 2)
    return {"tiers": tiers,
            "loglog_slope_t_tree_M_ge_3072": round(slope_t, 6),
            "loglog_slope_peak_rss_top_two_tiers": round(slope_r_top, 6),
            "note": ("pdist + scipy Ward (nearest-neighbour chain) holds two condensed float64 distance "
                     "arrays, 8*M*(M-1) bytes; tiers up to M = 12,288 ran 16 concurrent workers, "
                     "24,576 ran 4, 49,152 ran 1 (times below 49,152 include memory-bandwidth contention)"),
            "next_doubling_M": nxt,
            "next_doubling_two_copies_gb": round(8.0 * nxt * (nxt - 1) / 1e9, 1)}


def unknown_k(configs):
    out = {}
    for cond in ("favorable", "adverse"):
        cs = [c for c in configs if c["cond"] == cond]
        gap = np.array([c["ari_silK"][0] - c["ari_oracle"][0] for c in cs])
        by_w = []
        for W in (6, 12, 24, 48, 96):
            cw = [c for c in cs if c["W"] == W and c["M"] >= 3072]
            by_w.append({"W": W, "cells_M_ge_3072": len(cw),
                         "mean_oracle": round(float(np.mean([c["ari_oracle"][0] for c in cw])), 6),
                         "mean_silK": round(float(np.mean([c["ari_silK"][0] for c in cw])), 6)})
        worst = sorted(cs, key=lambda c: c["ari_silK"][0] - c["ari_oracle"][0])[:10]
        out[cond] = {"cells": len(cs),
                     "gap_mean": round(float(gap.mean()), 6), "gap_min": round(float(gap.min()), 6),
                     "gap_max": round(float(gap.max()), 6),
                     "cells_within_0.02": int((np.abs(gap) <= 0.02).sum()),
                     "cells_within_0.05": int((np.abs(gap) <= 0.05).sum()),
                     "cells_silK_below_oracle_by_gt_0.05": int((gap < -0.05).sum()),
                     "cells_silK_above_oracle_by_gt_0.02": int((gap > 0.02).sum()),
                     "by_W_M_ge_3072": by_w,
                     "worst10": [{"M": c["M"], "K": c["K"], "W": c["W"], "oracle": c["ari_oracle"][0],
                                  "silK": c["ari_silK"][0], "khat_mean": c["khat_mean"]} for c in worst]}
    return out


def _schedule_labels(M, K, W, seed, corr=0.0, p_award=0.5):
    """Replays pilot2e_boundary.gen_joint's RNG stream up to the pool schedules (identical draws)
    and labels each DER by its pool's award schedule, merging pools whose schedules coincide."""
    rng = np.random.default_rng(seed)
    pools = np.array([i % K for i in range(M)]); rng.shuffle(pools)
    thr = norm.ppf(1.0 - p_award)
    z_shared = rng.standard_normal(W)
    sched = {}
    for k in range(K):
        z_own = rng.standard_normal(W)
        g = np.sqrt(corr) * z_shared + np.sqrt(1.0 - corr) * z_own
        sched[k] = tuple((g > thr).astype(int))
    ids = {s: i for i, s in enumerate(sorted(set(sched.values())))}
    return pools, np.array([ids[sched[p]] for p in pools]), len(ids)


def collision(configs):
    """EXPLORATORY. Favorable condition (corr 0, gamma 1): pools with identical schedules emit
    identically distributed traffic, so no method can separate them; ARI(true, schedule-merged)
    is the resulting ceiling."""
    out = []
    for W in (6, 12):
        for K in (2, 4, 8, 16, 32, 64):
            for M in (3072, 12288):
                c = cell(configs, "favorable", K, W, M)
                if c is None:
                    continue
                a, nd = [], []
                for s in range(c["n"]):
                    true, merged, D = _schedule_labels(M, K, W, s)
                    a.append(ari(true, merged)); nd.append(D)
                out.append({"W": W, "K": K, "M": M, "possible_schedules": 2 ** W,
                            "distinct_schedules_mean": round(float(np.mean(nd)), 6),
                            "collision_ceiling_ari": round(float(np.mean(a)), 6),
                            "oracle": c["ari_oracle"][0], "silK": c["ari_silK"][0]})
    return out


def main():
    rows, configs = load()
    # "prereg" keeps the label recorded in the stored results; in this package the file is revision/prereg_E7_E8.md
    out = {"prereg": "reference/revision_r1/prereg_E7_E8.md", "runs": len(rows),
           "ari_vs_M": ari_vs_M(configs),
           "kw_at_M12288": kw_grid(configs, 12288),
           "kw_at_M49152": kw_grid(configs, 49152),
           "cost": cost(rows),
           "unknown_k": unknown_k(configs),
           "collision_EXPLORATORY": collision(configs)}
    json.dump(out, open(os.path.join(RES, "pilot2t_scale_analysis.json"), "w"), indent=2)

    fav = [c for c in configs if c["cond"] == "favorable" and c["W"] >= 24]
    print(f"runs {len(rows)}; favorable W>=24: min oracle {min(c['ari_oracle'][0] for c in fav):.4f}, "
          f"min silK {min(c['ari_silK'][0] for c in fav):.4f} over {len(fav)} cells")
    for K in (2, 4, 8, 16, 32, 64):
        a96, a24 = cell(configs, "adverse", K, 96, 49152), cell(configs, "adverse", K, 24, 49152)
        print(f"adverse M=49152 K={K:2d}: W96 oracle {a96['ari_oracle'][0]:.3f} silK {a96['ari_silK'][0]:.3f} | "
              f"W24 oracle {a24['ari_oracle'][0]:.3f} silK {a24['ari_silK'][0]:.3f}")
    c = out["cost"]
    print(f"cost: t_tree slope {c['loglog_slope_t_tree_M_ge_3072']}, rss slope (top two) "
          f"{c['loglog_slope_peak_rss_top_two_tiers']}; next doubling {c['next_doubling_M']} needs "
          f"{c['next_doubling_two_copies_gb']} GB for the two distance arrays alone")
    for t in c["tiers"][-3:]:
        print("  ", t)
    for cond, u in out["unknown_k"].items():
        print(f"unknown K, {cond}: {u['cells']} cells, within 0.02: {u['cells_within_0.02']}, "
              f"silK < oracle-0.05: {u['cells_silK_below_oracle_by_gt_0.05']}, "
              f"silK > oracle+0.02: {u['cells_silK_above_oracle_by_gt_0.02']}, "
              f"gap range [{u['gap_min']}, {u['gap_max']}]")
    print(f"saved -> {RES}/pilot2t_scale_analysis.json")


if __name__ == "__main__":
    main()
