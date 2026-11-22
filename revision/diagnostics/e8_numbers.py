"""e8_numbers.py -- every E8 number the manuscript text cites, computed from the per-run records (pilot2s_scale.jsonl)
of one observer. Descriptive summaries of the pre-registered grid; thresholds such as "true-K ARI at least 0.9" or
"3,072 DERs or more" are descriptive cuts chosen when writing, and the text says so.
Run: python revision/diagnostics/e8_numbers.py pilot/results_countonly
     python revision/diagnostics/e8_numbers.py pilot/results   (bidirectional variant)
Writes e8_numbers_<results dir name>.json next to this script.
"""
import json, os, sys
from collections import defaultdict
import numpy as np
from scipy.stats import ttest_ind

RES = os.path.abspath(sys.argv[1])
g = defaultdict(lambda: {"o": [], "s": [], "k": []})
for line in open(os.path.join(RES, "pilot2s_scale.jsonl")):
    if line.strip():
        r = json.loads(line)
        k = (r["cond"], r["M"], r["K"], r["W"])
        g[k]["o"].append(r["ari_oracle"]); g[k]["s"].append(r["ari_silK"]); g[k]["k"].append(r["khat"])
C = {k: {"o": float(np.mean(v["o"])), "osd": float(np.std(v["o"])), "s": float(np.mean(v["s"])), "ssd": float(np.std(v["s"])),
         "n": len(v["o"]), "ko": v["o"], "khat": v["k"]} for k, v in g.items()}
MS = [24 * 2 ** i for i in range(12)]
r4 = lambda x: round(float(x), 4)
out = {"results": os.path.basename(RES), "runs": sum(c["n"] for c in C.values()), "configs": len(C)}

# A. favorable timing
fav = {k: c for k, c in C.items() if k[0] == "favorable"}
out["fav_min_oracle_W_ge_24"] = r4(min(c["o"] for k, c in fav.items() if k[3] >= 24))
out["fav_W6_oracle_by_K_at_12288"] = {K: r4(fav[("favorable", 12288, K, 6)]["o"]) for K in (2, 4, 8, 16, 32, 64)}

# B. adverse timing, adding members at a fixed pool count
adv = {k: c for k, c in C.items() if k[0] == "adverse"}
members = {}
for K in (2, 4, 8, 16, 32, 64):
    for W in (24, 96):
        pts = [(M, adv[("adverse", M, K, W)]) for M in MS if ("adverse", M, K, W) in adv]
        means = [c["o"] for _, c in pts]
        # largest drop from any fleet size to any larger one, and its Welch test
        drop = max(((means[i] - means[j], i, j) for i in range(len(pts)) for j in range(i + 1, len(pts))), default=(0, 0, 0))
        p = ttest_ind(pts[drop[1]][1]["ko"], pts[drop[2]][1]["ko"], equal_var=False).pvalue if drop[0] > 0 else None
        members[f"K{K}_W{W}"] = {"M_min": pts[0][0], "at_M_min": r4(means[0]), "M_max": pts[-1][0], "at_M_max": r4(means[-1]),
                                 "sd_at_M_max": r4(pts[-1][1]["osd"]), "n_at_M_max": pts[-1][1]["n"],
                                 "max_drop": r4(drop[0]), "drop_from_M": pts[drop[1]][0], "drop_to_M": pts[drop[2]][0],
                                 "drop_from": r4(means[drop[1]]), "drop_to": r4(means[drop[2]]),
                                 "drop_welch_p": None if p is None else float(f"{p:.2g}"),
                                 "largest_ge_smallest": bool(means[-1] >= means[0] - 1e-9),
                                 "curve": [[M, r4(c["o"]), r4(c["osd"]), c["n"]] for M, c in pts]}
out["adverse_members"] = members

# C. adverse timing, adding pools at 768 DERs per pool
out["adverse_pools_768"] = {f"W{W}": [[K, 768 * K, r4(adv[("adverse", 768 * K, K, W)]["o"]), r4(adv[("adverse", 768 * K, K, W)]["osd"]),
                                       r4(adv[("adverse", 768 * K, K, W)]["s"]), adv[("adverse", 768 * K, K, W)]["n"]]
                                      for K in (2, 4, 8, 16, 32, 64)] for W in (24, 96)}

# D. adverse timing with 12 or fewer windows
low = {k: c for k, c in adv.items() if k[3] <= 12}
mx = max(low.items(), key=lambda kv: kv[1]["o"])
out["adverse_W_le_12_max_oracle"] = {"value": r4(mx[1]["o"]), "M": mx[0][1], "K": mx[0][2], "W": mx[0][3]}
out["adverse_K2_W6_trend"] = [[M, r4(adv[("adverse", M, 2, 6)]["o"])] for M in MS if ("adverse", M, 2, 6) in adv]
flat = {}
for K in (16, 32, 64):
    pts = [adv[("adverse", M, K, 6)]["o"] for M in MS if ("adverse", M, K, 6) in adv]
    flat[f"K{K}_W6_first_last"] = [r4(pts[0]), r4(pts[-1])]
out["adverse_W6_many_pools"] = flat

# E. estimating K
gap = lambda c: c["s"] - c["o"]
out["fav_configs"] = len(fav)
out["fav_within_0.05"] = sum(abs(gap(c)) <= 0.05 for c in fav.values())
out["fav_max_abs_gap"] = r4(max(abs(gap(c)) for c in fav.values()))
strong = [c for c in adv.values() if c["o"] >= 0.9]
out["adv_strong_configs"] = len(strong)
out["adv_strong_max_abs_gap"] = r4(max(abs(gap(c)) for c in strong))
loss = max(adv.items(), key=lambda kv: -gap(kv[1]))
out["adv_max_loss"] = {"loss": r4(-gap(loss[1])), "M": loss[0][1], "K": loss[0][2], "W": loss[0][3],
                       "oracle": r4(loss[1]["o"]), "silK": r4(loss[1]["s"])}
gain = max(adv.items(), key=lambda kv: gap(kv[1]))
out["adv_max_gain"] = {"gain": r4(gap(gain[1])), "M": gain[0][1], "K": gain[0][2], "W": gain[0][3],
                       "oracle": r4(gain[1]["o"]), "silK": r4(gain[1]["s"]),
                       "khat_mean": r4(np.mean(gain[1]["khat"]))}
w48 = {k: c for k, c in adv.items() if k[3] >= 48}
big = {k: c for k, c in w48.items() if k[1] >= 3072}
out["adv_W_ge_48_M_ge_3072_max_loss"] = r4(max(-gap(c) for c in big.values()))
lossy = [(k, -gap(c)) for k, c in w48.items() if -gap(c) > 0.05]
out["adv_W_ge_48_loss_gt_0.05"] = {"configs": len(lossy), "max": r4(max((x for _, x in lossy), default=0)),
                                   "M_max": max((k[1] for k, _ in lossy), default=None)}
low24 = {k: c for k, c in adv.items() if k[3] <= 24}
out["adv_W_le_24_loss_share"] = r4(np.mean([gap(c) < 0 for c in low24.values()]))
# where the estimated K misses: share of runs choosing fewer or more pools than the truth, by fleet size class (adverse, true-K ARI < 0.9)
split = {}
for name, lo, hi in (("M_le_384", 0, 384), ("M_768_6144", 768, 6144), ("M_ge_12288", 12288, 10 ** 9)):
    ks = [(k[2], kh) for k, c in adv.items() if lo <= k[1] <= hi and c["o"] < 0.9 for kh in c["khat"]]
    split[name] = {"runs": len(ks), "under": r4(np.mean([kh < K for K, kh in ks])), "over": r4(np.mean([kh > K for K, kh in ks])),
                   "to_two": r4(np.mean([kh == 2 and K > 2 for K, kh in ks]))}
out["adv_weak_split"] = split
cap = sum(sum(kh == min(96, k[1] // 2) for kh in c["khat"]) for k, c in C.items())
out["khat_at_candidate_cap_runs"] = int(cap)

# F. cost (from the analysis file)
t = json.load(open(os.path.join(RES, "pilot2t_scale_analysis.json")))["cost"]["tiers"]
out["cost"] = [{k: x[k] for k in ("M", "concurrent_workers", "t_tree_median_s", "t_tree_max_s", "peak_rss_gb", "two_condensed_copies_gb")} for x in t]
for M in (65536, 98304):
    out[f"two_condensed_copies_gb_M{M}"] = round(2 * M * (M - 1) / 2 * 8 / 1e9, 1)

name = "e8_numbers_" + os.path.basename(RES) + ".json"
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), name), "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ("adverse_members",)}, indent=1)[:6000])
for k, v in out["adverse_members"].items():
    print(k, {x: v[x] for x in v if x != "curve"})
