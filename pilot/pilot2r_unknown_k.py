"""
pilot2r_unknown_k.py -- E7 (revision R1, Reviewer 1 comment 1): membership recovery when the
attacker does NOT know the number of dispatch pools K.

Design fixed in revision/prereg_E7_E8.md before any ARI was computed.
Same generators, features, seeds, and Ward tree as the published results; three recovery methods:
  oracle : Ward cut at the true K (the published pipeline; must reproduce pilot2i / pilot2k ARI)
  silK   : Ward cut at K_hat = argmax silhouette over {2..min(96, M//2)} (rule ignores the true K)
  hdbscan: HDBSCAN(min_cluster_size=5), no K input; noise points kept as one group
Metric: ARI (pilot2i_metrics.ari). Also K_hat exact-match rate, mean |K_hat - K|, mean K_hat.

Saves results/pilot2r_unknown_k.json.  Run: python pilot2r_unknown_k.py
The helpers ward_tree() and select_k_silhouette() are reused by pilot2s_scale.py (E8).
"""
from __future__ import annotations
import json, os
import numpy as np
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import linkage, fcluster
from sklearn.metrics import silhouette_score
from sklearn.cluster import HDBSCAN
from pilot2_command_channel import gen, SEEDS
from pilot2e_boundary import gen_joint
from pilot2i_metrics import ari

RES = os.environ.get("CYE_RESULTS") or os.path.join(os.path.dirname(__file__), "results"); os.makedirs(RES, exist_ok=True)
KMAX_CAP = 96          # candidate K upper cap (pre-registered)
SIL_SUBSAMPLE = 6144   # silhouette on a fixed random subsample above this M (pre-registered)


def candidates(M):
    """Pre-registered candidate set for K_hat; depends only on M, never on the true K."""
    return list(range(2, min(KMAX_CAP, M // 2) + 1))


def ward_tree(feat):
    """Exactly the published clustering tree (pilot2_command_channel.cluster)."""
    return linkage(pdist(feat, metric="euclidean"), method="ward")


def select_k_silhouette(feat, Z, seed):
    """K_hat = argmax silhouette over candidates(M); ties -> smallest K; degenerate cuts skipped."""
    M = feat.shape[0]
    if M <= SIL_SUBSAMPLE:
        idx = None
        S = squareform(pdist(feat, metric="euclidean"))
    else:
        idx = np.sort(np.random.default_rng(10**6 + seed).choice(M, SIL_SUBSAMPLE, replace=False))
        S = squareform(pdist(feat[idx], metric="euclidean"))
    best_k, best_s = None, -np.inf
    for k in candidates(M):
        lab = fcluster(Z, k, criterion="maxclust")
        sub = lab if idx is None else lab[idx]
        n = np.unique(sub).size
        if n < 2 or n > sub.size - 1:
            continue
        s = silhouette_score(S, sub, metric="precomputed")
        if s > best_s:
            best_k, best_s = k, s
    if best_k is None:
        best_k = 2
    return best_k, fcluster(Z, best_k, criterion="maxclust")


def evaluate(gen_fn, K, n_seeds=SEEDS):
    """Run all three methods over n_seeds realizations of gen_fn(seed) -> (feat, true)."""
    r_or, r_sk, r_hd, khat, hd_n, hd_noise = [], [], [], [], [], []
    for s in range(n_seeds):
        feat, true = gen_fn(s)
        Z = ward_tree(feat)
        r_or.append(ari(true, fcluster(Z, K, criterion="maxclust")))
        k_hat, lab = select_k_silhouette(feat, Z, s)
        r_sk.append(ari(true, lab)); khat.append(k_hat)
        h = HDBSCAN(min_cluster_size=5, copy=True).fit_predict(feat)
        r_hd.append(ari(true, h))
        hd_n.append(int(np.unique(h[h >= 0]).size)); hd_noise.append(float(np.mean(h < 0)))
    ms = lambda x: [round(float(np.mean(x)), 6), round(float(np.std(x)), 6)]
    khat = np.array(khat)
    return {"ari_oracle": ms(r_or), "ari_silK": ms(r_sk), "ari_hdbscan": ms(r_hd),
            "khat_exact": round(float(np.mean(khat == K)), 6),
            "khat_mae": round(float(np.mean(np.abs(khat - K))), 6),
            "khat_mean": round(float(np.mean(khat)), 6),
            "hdb_nclust_mean": round(float(np.mean(hd_n)), 6),
            "hdb_noise_frac": round(float(np.mean(hd_noise)), 6)}


def main():
    pts = []

    def add(group, label, K, gen_fn, meta):
        r = evaluate(gen_fn, K)
        pts.append({"group": group, "label": label, "K": K,
                    **{k: v for k, v in meta.items() if k != "K"}, **r})
        print(f"[{group}] {label:<38} oracle={r['ari_oracle'][0]:.3f}  silK={r['ari_silK'][0]:.3f}  "
              f"hdb={r['ari_hdbscan'][0]:.3f}  Khat_exact={r['khat_exact']:.2f} (mean {r['khat_mean']})",
              flush=True)

    # P1: the six published operating points (as in pilot2i_metrics.py)
    for label, kw in [
        ("headline (corr0, g1, W24, K2)",      dict(corr=0.0,  gamma=1.0,  W=24, K=2, M=24)),
        ("mild K2 (corr0.5, g0.75, W16, K2)",  dict(corr=0.5,  gamma=0.75, W=16, K=2, M=24)),
        ("mild K5 (corr0.5, g0.75, W16, K5)",  dict(corr=0.5,  gamma=0.75, W=16, K=5, M=30)),
        ("SOC-budget (corr0.5, g0.5, W8, K5)", dict(corr=0.5,  gamma=0.5,  W=8,  K=5, M=30)),
        ("battery (corr0.75, g0.5, W8, K5)",   dict(corr=0.75, gamma=0.5,  W=8,  K=5, M=30)),
        ("pessimistic (corr0.75,g0.5,W4,K5)",  dict(corr=0.75, gamma=0.5,  W=4,  K=5, M=30)),
    ]:
        add("P1", label, kw["K"], lambda s, kw=kw: gen_joint(seed=s, **kw), kw)

    # P2: published correlation sweep (gamma 1, W 24, K 2, M 24)
    for c in [0.0, 0.5, 0.9, 0.99, 1.0]:
        kw = dict(corr=c, gamma=1.0, W=24, K=2, M=24)
        add("P2", f"corr={c}", 2, lambda s, kw=kw: gen_joint(seed=s, **kw), kw)

    # P3: published synchronization sweep (corr 0, W 24)
    for K, M in [(2, 24), (5, 30)]:
        for g in [1.0, 0.75, 0.5, 0.25, 0.0]:
            kw = dict(corr=0.0, gamma=g, W=24, K=K, M=M)
            add("P3", f"gamma={g} K={K}", K, lambda s, kw=kw: gen_joint(seed=s, **kw), kw)

    # P4: pool-count sweep, favorable
    for K in [2, 3, 4, 5, 6, 8]:
        kw = dict(corr=0.0, gamma=1.0, W=24, K=K, M=max(24, 6 * K))
        add("P4", f"K={K} (M={kw['M']})", K, lambda s, kw=kw: gen_joint(seed=s, **kw), kw)

    # P5: observation-budget sweep, favorable, K 5, M 30
    for W in [4, 8, 16, 24, 48]:
        kw = dict(corr=0.0, gamma=1.0, W=W, K=5, M=30)
        add("P5", f"W={W} K=5", 5, lambda s, kw=kw: gen_joint(seed=s, **kw), kw)

    # P6: negative control, no pool structure
    for K in [2, 3, 5, 8]:
        M = max(24, 6 * K)
        add("P6", f"no-structure K={K} (M={M})", K,
            lambda s, K=K, M=M: gen(no_pools=True, K=K, M=M, seed=s), dict(M=M, W=24))

    # "prereg" keeps the label recorded in the stored results; in this package the file is revision/prereg_E7_E8.md
    out = {"prereg": "reference/revision_r1/prereg_E7_E8.md", "n_seeds": SEEDS,
           "kmax_cap": KMAX_CAP, "points": pts}
    json.dump(out, open(os.path.join(RES, "pilot2r_unknown_k.json"), "w"), indent=2)
    print(f"\nsaved -> {RES}/pilot2r_unknown_k.json")


if __name__ == "__main__":
    main()
