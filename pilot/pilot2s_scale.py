"""
pilot2s_scale.py -- E8 (revision R1, Reviewer 1 comment 2 + Reviewer 4 comment 2): membership
recovery and clustering cost as the aggregation grows from 24 to 49,152 DERs.

Design fixed in revision/prereg_E7_E8.md before any ARI was computed.
Same generator (pilot2e_boundary.gen_joint), features, Ward tree, and silhouette K-selection as E7
(imported from pilot2r_unknown_k). Two methods: oracle (true K) and silK (K_hat by silhouette).

Grid: M = 24*2^i (i=0..11); K in {2,4,8,16,32,64} with M >= 3K; W in {6,12,24,48,96} for
M <= 12288 else {24,96}; conditions favorable (corr 0, gamma 1) / adverse (corr 0.5, gamma 0.6);
seeds 20 (M <= 6144), 10 (M = 12288), 5 (M >= 24576).

Each run appends one JSON line to results/pilot2s_scale.jsonl (resumable: finished runs are
skipped). Tiers run in ascending M, each in a fresh process pool sized to a memory budget.
At the end, results/pilot2s_scale.json holds per-configuration means and per-tier cost.
Run: python pilot2s_scale.py
"""
from __future__ import annotations
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")          # parallel workers: one BLAS thread each
import json, resource, time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from scipy.cluster.hierarchy import fcluster

RES = os.environ.get("CYE_RESULTS") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
JSONL = os.path.join(RES, "pilot2s_scale.jsonl")
SUMMARY = os.path.join(RES, "pilot2s_scale.json")
MEM_BUDGET_GB = 34.0     # leave headroom on the 48 GB machine
MAX_WORKERS = 16

MS = [24 * 2 ** i for i in range(12)]                     # 24 .. 49152
KS = [2, 4, 8, 16, 32, 64]
CONDS = {"favorable": (0.0, 1.0), "adverse": (0.5, 0.6)}  # (corr, gamma)


def ws_for(M):
    return [6, 12, 24, 48, 96] if M <= 12288 else [24, 96]


def seeds_for(M):
    return 20 if M <= 6144 else (10 if M == 12288 else 5)


def est_gb(M):
    # conservative per-worker peak: measured ~1.4 GB @12288, ~6.3 GB @24576, ~17.7 GB @49152
    return 1.1e-8 * M * M + 0.4


def workers_for(M):
    return max(1, min(MAX_WORKERS, int(MEM_BUDGET_GB // est_gb(M))))


def key(M, K, W, cond, seed):
    return f"{M}|{K}|{W}|{cond}|{seed}"


def run_one(M, K, W, cond, seed):
    from pilot2e_boundary import gen_joint
    from pilot2i_metrics import ari
    from pilot2r_unknown_k import ward_tree, select_k_silhouette
    corr, gamma = CONDS[cond]
    feat, true = gen_joint(corr=corr, gamma=gamma, M=M, K=K, W=W, seed=seed)
    t0 = time.perf_counter(); Z = ward_tree(feat); t_tree = time.perf_counter() - t0
    a_or = ari(true, fcluster(Z, K, criterion="maxclust"))
    t0 = time.perf_counter(); k_hat, lab = select_k_silhouette(feat, Z, seed); t_sel = time.perf_counter() - t0
    a_sk = ari(true, lab)
    return {"M": M, "K": K, "W": W, "cond": cond, "seed": seed,
            "ari_oracle": round(float(a_or), 5), "ari_silK": round(float(a_sk), 5), "khat": int(k_hat),
            "t_tree": round(t_tree, 3), "t_sel": round(t_sel, 3),
            "rss_gb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9, 3)}


def all_tasks():
    tasks = []
    for M in MS:
        for K in KS:
            if M < 3 * K:
                continue
            for W in ws_for(M):
                for cond in CONDS:
                    for seed in range(seeds_for(M)):
                        tasks.append((M, K, W, cond, seed))
    return tasks


def load_done():
    done = {}
    if os.path.exists(JSONL):
        for line in open(JSONL):
            line = line.strip()
            if line:
                r = json.loads(line)
                done[key(r["M"], r["K"], r["W"], r["cond"], r["seed"])] = r
    return done


def summarize(rows):
    g = defaultdict(list)
    for r in rows:
        g[(r["M"], r["K"], r["W"], r["cond"])].append(r)
    configs = []
    for (M, K, W, cond), rs in sorted(g.items()):
        ao = [r["ari_oracle"] for r in rs]; ak = [r["ari_silK"] for r in rs]
        kh = np.array([r["khat"] for r in rs])
        configs.append({"M": M, "K": K, "W": W, "cond": cond, "n": len(rs),
                        "ari_oracle": [round(float(np.mean(ao)), 4), round(float(np.std(ao)), 4)],
                        "ari_silK": [round(float(np.mean(ak)), 4), round(float(np.std(ak)), 4)],
                        "khat_exact": round(float(np.mean(kh == K)), 3),
                        "khat_mean": round(float(np.mean(kh)), 2)})
    tiers = []
    for M in MS:
        rs = [r for r in rows if r["M"] == M]
        if rs:
            tiers.append({"M": M, "runs": len(rs),
                          "t_tree_mean_s": round(float(np.mean([r["t_tree"] for r in rs])), 3),
                          "t_sel_mean_s": round(float(np.mean([r["t_sel"] for r in rs])), 3),
                          "peak_rss_gb": round(float(max(r["rss_gb"] for r in rs)), 2)})
    # "prereg" keeps the label recorded in the stored results; in this package the file is revision/prereg_E7_E8.md
    return {"prereg": "reference/revision_r1/prereg_E7_E8.md", "configs": configs, "tiers": tiers}


def main():
    os.makedirs(RES, exist_ok=True)
    done = load_done()
    tasks = [t for t in all_tasks() if key(*t) not in done]
    print(f"E8 scale: {len(all_tasks())} runs total, {len(done)} already done, {len(tasks)} to run", flush=True)
    by_m = defaultdict(list)
    for t in tasks:
        by_m[t[0]].append(t)
    with open(JSONL, "a") as fh:
        for M in sorted(by_m):
            w = workers_for(M); t_start = time.perf_counter(); n = len(by_m[M])
            print(f"[tier M={M}] {n} runs on {w} worker(s) ...", flush=True)
            with ProcessPoolExecutor(max_workers=w) as ex:
                futs = [ex.submit(run_one, *t) for t in by_m[M]]
                for i, f in enumerate(as_completed(futs), 1):
                    r = f.result()
                    fh.write(json.dumps(r) + "\n"); fh.flush()
                    if i % max(1, n // 4) == 0 or i == n:
                        print(f"   {i}/{n} done ({time.perf_counter() - t_start:.0f}s)", flush=True)
            print(f"[tier M={M}] finished in {time.perf_counter() - t_start:.0f}s", flush=True)
    rows = list(load_done().values())
    json.dump(summarize(rows), open(SUMMARY, "w"), indent=2)
    print(f"saved -> {SUMMARY}", flush=True)


if __name__ == "__main__":
    main()
