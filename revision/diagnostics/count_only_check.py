"""count_only_check.py -- DIAGNOSTIC (not pre-registered), 2026-10-28, prompted by Codex finding F1.
The main sweeps cluster on [z(count), z(size)] where idle records are telemetry-sized (300 B), while the
manuscript describes the primary feature as the downlink record count. This script re-scores the paper's main
operating points with the count block alone (feat[:, :W], i.e. the downlink-only observer: in the downlink model
idle records are setpoint-sized, so size carries no activity) and reports the ARI difference. Same generators,
same seeds (50), same Ward oracle-K cut. Run: python revision/diagnostics/count_only_check.py"""
import json, os, sys
import numpy as np
from scipy.cluster.hierarchy import fcluster
sys.path.insert(0, os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."), "pilot"))
from pilot2e_boundary import gen_joint
from pilot2_command_channel import gen
from pilot2r_unknown_k import ward_tree, select_k_silhouette
from pilot2i_metrics import ari

SEEDS = range(50)
def score(gen_fn, K, W, use_silk=False):
    both, cnt, both_sk, cnt_sk = [], [], [], []
    for s in SEEDS:
        feat, true = gen_fn(s)
        for f, a, b in ((feat, both, both_sk), (feat[:, :W], cnt, cnt_sk)):
            Z = ward_tree(f); a.append(ari(true, fcluster(Z, K, "maxclust")))
            if use_silk: b.append(ari(true, select_k_silhouette(f, Z, s)[1]))
    out = {"both": round(float(np.mean(both)), 4), "count_only": round(float(np.mean(cnt)), 4)}
    if use_silk: out.update(both_silK=round(float(np.mean(both_sk)), 4), count_only_silK=round(float(np.mean(cnt_sk)), 4))
    return out

pts = []
def J(label, corr, gamma, W, K, M, silk=True):
    pts.append((label, K, W, (lambda s, c=corr, g=gamma, w=W, k=K, m=M: gen_joint(corr=c, gamma=g, M=m, K=k, W=w, seed=s)), silk))
J("headline corr0 g1 W24 K2", 0.0, 1.0, 24, 2, 24)
for c in (0.5, 0.9, 0.99, 1.0): J(f"corr sweep c={c} W24 K2", c, 1.0, 24, 2, 24)
for g in (0.75, 0.5, 0.25): J(f"gamma sweep g={g} K2", 0.0, g, 24, 2, 24); J(f"gamma sweep g={g} K5", 0.0, g, 24, 5, 30)
J("mild K2 (c.5 g.75 W16)", 0.5, 0.75, 16, 2, 24); J("mild K5 (c.5 g.75 W16)", 0.5, 0.75, 16, 5, 30)
J("SoC stress (c.5 g.5 W8 K5)", 0.5, 0.5, 8, 5, 30); J("pessimistic (c.75 g.5 W4 K5)", 0.75, 0.5, 4, 5, 30)
for W in (8, 16, 32, 64, 128): J(f"stressed budget W={W} (c.5 g.5 K5)", 0.5, 0.5, W, 5, 30, silk=False)
for W in (2, 4, 8): pts.append((f"E4 cost corner W={W} K2 (gen)", 2, W, (lambda s, w=W: gen(M=24, K=2, W=w, seed=s)), False))
pts.append(("E2 real (gen) K2 W24", 2, 24, (lambda s: gen(M=24, K=2, W=24, seed=s)), False))
pts.append(("E6 no pools (gen) K2", 2, 24, (lambda s: gen(M=24, K=2, W=24, seed=s, no_pools=True)), False))

rows = []
for label, K, W, fn, silk in pts:
    r = score(fn, K, W, silk); r["point"] = label; r["diff_oracle"] = round(r["count_only"] - r["both"], 4); rows.append(r)
    print(f"{label:<36} both {r['both']:.4f}  count-only {r['count_only']:.4f}  diff {r['diff_oracle']:+.4f}"
          + (f" | silK both {r['both_silK']:.4f} count {r['count_only_silK']:.4f}" if silk else ""))
d = [abs(r["diff_oracle"]) for r in rows]
print(f"max |count-only - both| (true K) = {max(d):.4f} over {len(rows)} points")
json.dump(rows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "count_only_check.json"), "w"), indent=1)
