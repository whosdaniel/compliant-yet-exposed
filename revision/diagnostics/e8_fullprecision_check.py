"""e8_fullprecision_check.py -- full-precision re-run of one E8 configuration whose stored per-run ARIs (five decimals)
average to a two-decimal tie: adverse timing, 49,152 DERs, 64 pools, 96 windows, seeds 0 to 4, downlink observer.
Same code path as pilot2s_scale.run_one (generator, Ward tree, silhouette selection), without rounding the ARI.
Also confirms that the five-decimal values match the stored jsonl. About 4 minutes, about 21 GB of memory.
Run: CYE_FEATURES=count python revision/diagnostics/e8_fullprecision_check.py
"""
import json, os, sys
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")                     # as in pilot2s_scale.py
import numpy as np
from scipy.cluster.hierarchy import fcluster
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, ROOT + "/pilot")
from pilot2_command_channel import FEATURES
from pilot2e_boundary import gen_joint
from pilot2i_metrics import ari
from pilot2r_unknown_k import ward_tree, select_k_silhouette

assert FEATURES == "count", "run with CYE_FEATURES=count"
M, K, W, corr, gamma = 49152, 64, 96, 0.5, 0.6
stored = {}
for line in open(ROOT + "/pilot/results_countonly/pilot2s_scale.jsonl"):
    r = json.loads(line)
    if (r["cond"], r["M"], r["K"], r["W"]) == ("adverse", M, K, W):
        stored[r["seed"]] = (r["ari_oracle"], r["ari_silK"])
out = {"config": "adverse, M 49152, K 64, W 96, downlink observer", "runs": []}
for seed in sorted(stored):
    feat, true = gen_joint(corr=corr, gamma=gamma, M=M, K=K, W=W, seed=seed)
    Z = ward_tree(feat)
    a_or = float(ari(true, fcluster(Z, K, criterion="maxclust")))
    k_hat, lab = select_k_silhouette(feat, Z, seed)
    a_sk = float(ari(true, lab))
    same = (round(a_or, 5), round(a_sk, 5)) == stored[seed]
    out["runs"].append({"seed": seed, "ari_oracle": a_or, "ari_silK": a_sk, "khat": int(k_hat), "matches_stored_5dp": same})
    print(out["runs"][-1], flush=True)
out["mean_oracle"] = float(np.mean([r["ari_oracle"] for r in out["runs"]]))
out["mean_silK"] = float(np.mean([r["ari_silK"] for r in out["runs"]]))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "e8_fullprecision_check.json"), "w"), indent=2)
print("mean oracle", repr(out["mean_oracle"]), "| mean silK", repr(out["mean_silK"]))
