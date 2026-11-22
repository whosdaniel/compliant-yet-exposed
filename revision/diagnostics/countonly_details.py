"""countonly_details.py -- descriptive details the manuscript text cites but the result files do not store, recomputed
for the observer set by CYE_FEATURES (amendment 1). Same generators, seeds, and estimators as the result files; nothing is
tuned. (a) E7 mild five-pool point: per-seed silhouette K_hat split into under-, exact, and over-split, with each group's
share of the ARI lost against the true-K cut (cited as "under-split in N seeds and over-split in M"). (b) Drift run,
churn arm: unrounded mean ARI per W (the result file kept three decimals). (c) HDBSCAN clusters per seed at the mild points. Run once per observer:
  CYE_FEATURES=count python revision/diagnostics/countonly_details.py
  python revision/diagnostics/countonly_details.py      (count+size, must match the 21/5/24 split)
"""
import json, os, sys
import numpy as np
from scipy.cluster.hierarchy import fcluster
sys.path.insert(0, os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."), "pilot"))
from pilot2_command_channel import FEATURES, SEEDS, cluster
from pilot2e_boundary import gen_joint
from pilot2r_unknown_k import ward_tree, select_k_silhouette
from pilot2i_metrics import ari
from pilot2n_drift import gen_drift

out = {"features": FEATURES}

# (a) E7 mild K5 (corr 0.5, gamma 0.75, W 16, K 5, M 30), as in pilot2r_unknown_k.py P1
K = 5; rows = []
for s in range(SEEDS):
    feat, true = gen_joint(seed=s, corr=0.5, gamma=0.75, W=16, K=K, M=30)
    Z = ward_tree(feat)
    a_or = ari(true, fcluster(Z, K, criterion="maxclust"))
    k_hat, lab = select_k_silhouette(feat, Z, s)
    rows.append((k_hat, a_or, ari(true, lab)))
k = np.array([r[0] for r in rows]); loss = np.array([r[1] - r[2] for r in rows])
out["e7_mildK5"] = {
    "ari_oracle": round(float(np.mean([r[1] for r in rows])), 4), "ari_silK": round(float(np.mean([r[2] for r in rows])), 4),
    "n_under": int(np.sum(k < K)), "n_exact": int(np.sum(k == K)), "n_over": int(np.sum(k > K)),
    "mean_loss": round(float(np.mean(loss)), 4),
    "loss_from_under": round(float(np.sum(loss[k < K]) / len(k)), 4),
    "loss_from_over": round(float(np.sum(loss[k > K]) / len(k)), 4),
}

# (b) churn arm of the drift run (K 5, M 30, corr 0.5, gamma 0.5, 2% reassignment), unrounded mean ARI
out["churn_ari_unrounded"] = {}
for W in (8, 16, 32, 64, 128):
    v = [ari(t, cluster(f, 5)) for f, t in (gen_drift("churn", K=5, M=30, W=W, seed=s) for s in range(SEEDS))]
    out["churn_ari_unrounded"][W] = float(np.mean(v))

# (c) HDBSCAN outcome per seed at the two mild E7 points (cited as "every DER noise in half of the seeds, two clusters
#     in the rest"): number of clusters found, excluding noise
from sklearn.cluster import HDBSCAN
from collections import Counter
out["hdbscan_clusters_per_seed"] = {}
for name_, K_, M_ in (("mild K2", 2, 24), ("mild K5", 5, 30)):
    nc = []
    for s_ in range(SEEDS):
        f_, t_ = gen_joint(seed=s_, corr=0.5, gamma=0.75, W=16, K=K_, M=M_)
        h = HDBSCAN(min_cluster_size=5, copy=True).fit_predict(f_)
        nc.append(int(np.unique(h[h >= 0]).size))
    out["hdbscan_clusters_per_seed"][name_] = {str(k): v for k, v in sorted(Counter(nc).items())}

name = "countonly_details_" + FEATURES.replace("+", "_") + ".json"
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), name), "w"), indent=2)
print(json.dumps(out, indent=1))
