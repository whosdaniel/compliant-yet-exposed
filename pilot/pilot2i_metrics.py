"""
pilot2i_metrics.py -- chance-adjusted + permutation-calibrated re-analysis of the headline and the
boundary operating points. Addresses the point that optimal-assignment accuracy has
an INFLATED 1/K baseline: the paper's own E6 no-structure floor is 0.59/0.47/0.39/0.32 for
K=2/3/5/8, not 1/K = 0.50/0.33/0.20/0.125. Comparing a realistic operating point (0.45 at K=5)
against 0.20 overstates the effect ~2x; against the correct empirical floor (0.39) it is ~1.15x.

Over the SAME generators (pilot2_command_channel.gen / pilot2e_boundary.gen_joint), this adds three
things raw accuracy cannot give, so "above chance" is tested honestly:
  - ARI  (Adjusted Rand Index): chance-adjusted, ~0 under the null for ANY K, 1 at perfect.
  - pairwise co-membership precision/recall/F1: the attack's actual target ("are i,j co-members?").
  - a label-permutation null per realization: 97.5th-percentile null + permutation p-value for BOTH
    accuracy and ARI, at the exact same N, K, and clustering pipeline (no 1/K assumption anywhere).

Self-contained: numpy/scipy only (ARI and pairwise-F1 implemented here; no sklearn dependency).
Saves results/pilot2i_metrics.json. Run:  python pilot2i_metrics.py
"""
from __future__ import annotations
import json, os
import numpy as np
from pilot2_command_channel import cluster, accuracy, gen, SEEDS
from pilot2e_boundary import gen_joint

RES = os.path.join(os.path.dirname(__file__), "results"); os.makedirs(RES, exist_ok=True)
NPERM = 200


def _comb2(x):
    x = np.asarray(x, dtype=float)
    return x * (x - 1.0) / 2.0


def ari(a, b):
    """Adjusted Rand Index from the contingency table (no sklearn)."""
    a = np.asarray(a); b = np.asarray(b)
    ua = np.unique(a); ub = np.unique(b)
    cont = np.zeros((ua.size, ub.size), dtype=float)
    for i, va in enumerate(ua):
        for j, vb in enumerate(ub):
            cont[i, j] = np.sum((a == va) & (b == vb))
    sum_ij = np.sum(_comb2(cont.ravel()))
    ai = np.sum(_comb2(cont.sum(axis=1)))
    bj = np.sum(_comb2(cont.sum(axis=0)))
    n = a.size
    expected = ai * bj / _comb2([n])[0]
    maxidx = 0.5 * (ai + bj)
    denom = maxidx - expected
    return 1.0 if denom == 0 else float((sum_ij - expected) / denom)


def pairwise_prf(a, b):
    """Pairwise co-membership precision/recall/F1: predicted same-cluster (b) vs true same-pool (a)."""
    a = np.asarray(a); b = np.asarray(b); n = a.size
    iu = np.triu_indices(n, k=1)
    same_t = (a[iu[0]] == a[iu[1]]); same_p = (b[iu[0]] == b[iu[1]])
    tp = float(np.sum(same_t & same_p)); fp = float(np.sum(~same_t & same_p)); fn = float(np.sum(same_t & ~same_p))
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return prec, rec, f1


def perm_null(true, pred, K, rng, nperm=NPERM):
    """Label-permutation null for accuracy and ARI at this exact N, K, pipeline."""
    na = np.empty(nperm); nr = np.empty(nperm)
    for p in range(nperm):
        pt = rng.permutation(true)
        na[p] = accuracy(pt, pred, K)
        nr[p] = ari(pt, pred)
    return na, nr


def analyze(gen_fn, K, label):
    obs_acc, obs_ari, obs_f1 = [], [], []
    null_acc95, null_ari95, p_acc, p_ari = [], [], [], []
    for s in range(SEEDS):
        feat, true = gen_fn(s)
        pred = cluster(feat, K)
        oa = accuracy(true, pred, K); orr = ari(true, pred); _, _, of = pairwise_prf(true, pred)
        obs_acc.append(oa); obs_ari.append(orr); obs_f1.append(of)
        rng = np.random.default_rng(10_000 + s)
        na, nr = perm_null(true, pred, K, rng)
        null_acc95.append(np.percentile(na, 97.5)); null_ari95.append(np.percentile(nr, 97.5))
        p_acc.append((np.sum(na >= oa) + 1) / (NPERM + 1))
        p_ari.append((np.sum(nr >= orr) + 1) / (NPERM + 1))

    def ms(x): return [round(float(np.mean(x)), 4), round(float(np.std(x)), 4)]
    res = {
        "label": label, "K": K,
        "acc": ms(obs_acc), "ari": ms(obs_ari), "pairwise_f1": ms(obs_f1),
        "null_acc_p975_mean": round(float(np.mean(null_acc95)), 4),
        "null_ari_p975_mean": round(float(np.mean(null_ari95)), 4),
        "p_acc_median": round(float(np.median(p_acc)), 4),
        "p_ari_median": round(float(np.median(p_ari)), 4),
        "frac_sig_acc_p05": round(float(np.mean(np.array(p_acc) < 0.05)), 3),
        "frac_sig_ari_p05": round(float(np.mean(np.array(p_ari) < 0.05)), 3),
    }
    print(f"  {label:<40} acc={res['acc'][0]:.3f} ari={res['ari'][0]:.3f} f1={res['pairwise_f1'][0]:.3f} "
          f"| null_acc97.5={res['null_acc_p975_mean']:.3f} ari97.5={res['null_ari_p975_mean']:.3f} "
          f"| p_ari~{res['p_ari_median']:.3f} sigfrac={res['frac_sig_ari_p05']:.2f}")
    return res


def main():
    print(f"== pilot2i: chance-adjusted (ARI) + pairwise-F1 + permutation null ({SEEDS} seeds, {NPERM} perms) ==")
    points = [
        ("headline (corr0, g1, W24, K2)",      lambda s: gen_joint(corr=0.0,  gamma=1.0, W=24, K=2, M=24, seed=s), 2),
        ("mild K2 (corr0.5, g0.75, W16, K2)",  lambda s: gen_joint(corr=0.5,  gamma=0.75, W=16, K=2, M=24, seed=s), 2),
        ("mild K5 (corr0.5, g0.75, W16, K5)",  lambda s: gen_joint(corr=0.5,  gamma=0.75, W=16, K=5, M=30, seed=s), 5),
        ("SOC-budget (corr0.5, g0.5, W8, K5)", lambda s: gen_joint(corr=0.5,  gamma=0.5, W=8,  K=5, M=30, seed=s), 5),
        ("battery (corr0.75, g0.5, W8, K5)",   lambda s: gen_joint(corr=0.75, gamma=0.5, W=8,  K=5, M=30, seed=s), 5),
        ("pessimistic (corr0.75,g0.5,W4,K5)",  lambda s: gen_joint(corr=0.75, gamma=0.5, W=4,  K=5, M=30, seed=s), 5),
        ("E6 no-structure K2",                 lambda s: gen(no_pools=True, K=2, M=24, seed=s), 2),
        ("E6 no-structure K5",                 lambda s: gen(no_pools=True, K=5, M=30, seed=s), 5),
    ]
    out = {"n_seeds": SEEDS, "n_perm": NPERM, "points": [analyze(fn, K, lab) for lab, fn, K in points]}
    json.dump(out, open(os.path.join(RES, "pilot2i_metrics.json"), "w"), indent=2)
    print(f"\nsaved -> {RES}/pilot2i_metrics.json")
    print("-> ARI is chance-adjusted (~0 under null for any K); pairwise-F1 = the co-membership target;")
    print("   permutation p/null make 'above chance' honest vs the same-N,K floor (not 1/K).")


if __name__ == "__main__":
    main()
