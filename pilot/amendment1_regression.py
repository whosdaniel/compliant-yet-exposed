"""amendment1_regression.py -- regression check required by amendment 1 (revision/
prereg_amendment1_count_only.md) before any count-only run: with the default observer features
(CYE_FEATURES unset = count+size) the modified scripts must reproduce the stored results/ exactly,
every field except wall-clock timings and memory. E8 is checked by pilot2s_verify.py (sampled re-runs).

The scripts write into a scratch directory (CYE_RESULTS); the stored results/ are only read.
Run: python amendment1_regression.py <scratch_dir> <report.json>
"""
import json, os, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
STORED = os.path.join(HERE, "results")
PY = sys.executable
SCRIPTS = {   # script -> result file it writes
    "pilot2_command_channel.py": "pilot2_results.json",
    "pilot2b_correlation.py": "pilot2b_correlation.json",
    "pilot2c_sensitivity.py": "pilot2c_sensitivity.json",
    "pilot2d_within_pool.py": "pilot2d_within_pool.json",
    "pilot2e_boundary.py": "pilot2e_boundary.json",
    "pilot2f_nuisance.py": "pilot2f_nuisance.json",
    "pilot2h_disaggregation.py": "pilot2h_disaggregation.json",
    "pilot2i_metrics.py": "pilot2i_metrics.json",
    "pilot2j_wsweep.py": "pilot2j_wsweep.json",
    "pilot2k_ari_curves.py": "pilot2k_ari_curves.json",
    "pilot2m_psweep.py": "pilot2m_psweep.json",
    "pilot2n_drift.py": "pilot2n_drift.json",
    "pilot2o_fig_ari.py": "pilot2o_fig_ari.json",
    "pilot2r_unknown_k.py": "pilot2r_unknown_k.json",
}
TIMING_WORDS = ("time", "sec", "wall", "elapsed", "mem", "rss", "_gb", "peak")


def diff(a, b, path=""):
    """Every path where a and b differ (exact equality on leaves)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            p = f"{path}/{k}"
            if k not in a or k not in b:
                out.append((p, a.get(k, "<absent>"), b.get(k, "<absent>")))
            else:
                out += diff(a[k], b[k], p)
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [(path + "/<len>", len(a), len(b))]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in diff(x, y, f"{path}[{i}]")]
    return [] if a == b else [(path, a, b)]


def is_timing(path):
    return any(w in path.lower() for w in TIMING_WORDS)


def run(script, scratch, log_dir):
    env = dict(os.environ, CYE_RESULTS=scratch)
    env.pop("CYE_FEATURES", None)                      # default = count+size
    t0 = time.time()
    with open(os.path.join(log_dir, script + ".log"), "w") as log:
        rc = subprocess.run([PY, script], cwd=HERE, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    return script, rc, round(time.time() - t0, 1)


def main():
    scratch, report = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    os.makedirs(scratch, exist_ok=True)
    log_dir = os.path.join(scratch, "logs"); os.makedirs(log_dir, exist_ok=True)
    out = {"features": "count+size (default)", "scratch": scratch, "scripts": {}}

    with ThreadPoolExecutor(max_workers=6) as ex:
        for script, rc, sec in ex.map(lambda s: run(s, scratch, log_dir), SCRIPTS):
            print(f"{script:<28} rc={rc} {sec:>7.1f}s", flush=True)
            out["scripts"][script] = {"rc": rc, "seconds": sec}

    # E8 analysis reads the E8 run files: give it the stored ones, then compare its output
    for f in ("pilot2s_scale.jsonl", "pilot2s_scale.json"):
        shutil.copy2(os.path.join(STORED, f), os.path.join(scratch, f))
    _, rc, sec = run("pilot2t_scale_analysis.py", scratch, log_dir)
    out["scripts"]["pilot2t_scale_analysis.py"] = {"rc": rc, "seconds": sec}
    SCRIPTS["pilot2t_scale_analysis.py"] = "pilot2t_scale_analysis.json"
    print(f"{'pilot2t_scale_analysis.py':<28} rc={rc} {sec:>7.1f}s", flush=True)

    n_bad = 0
    for script, res in SCRIPTS.items():
        rec = out["scripts"][script]
        new_p = os.path.join(scratch, res)
        if rec["rc"] != 0 or not os.path.exists(new_p):
            rec["verdict"] = "FAILED TO RUN"; n_bad += 1; continue
        d = diff(json.load(open(os.path.join(STORED, res))), json.load(open(new_p)))
        result_diffs = [x for x in d if not is_timing(x[0])]
        rec["timing_or_memory_diffs"] = len(d) - len(result_diffs)
        rec["timing_or_memory_paths"] = [p for p, _, _ in d if is_timing(p)][:50]
        rec["result_diffs"] = [{"path": p, "stored": s, "rerun": r} for p, s, r in result_diffs[:50]]
        rec["n_result_diffs"] = len(result_diffs)
        rec["verdict"] = "MATCH" if not result_diffs else "MISMATCH"
        n_bad += bool(result_diffs)
        print(f"{res:<32} {rec['verdict']:<9} result diffs={len(result_diffs)} timing/memory diffs={rec['timing_or_memory_diffs']}")

    # E8: exact re-run of the fixed random sample of stored runs
    env = dict(os.environ); env.pop("CYE_FEATURES", None); env.pop("CYE_RESULTS", None)
    t0 = time.time()
    p = subprocess.run([PY, "pilot2s_verify.py"], cwd=HERE, env=env, capture_output=True, text=True)
    out["e8_sample"] = {"rc": p.returncode, "seconds": round(time.time() - t0, 1), "output": p.stdout.strip().splitlines()}
    e8_ok = p.returncode == 0 and "determinism: ALL MATCH" in p.stdout
    print(p.stdout)
    n_bad += not e8_ok

    out["overall"] = "PASS" if n_bad == 0 else f"FAIL ({n_bad} item(s))"
    json.dump(out, open(report, "w"), indent=2)
    print("overall:", out["overall"], "->", report)


if __name__ == "__main__":
    main()
