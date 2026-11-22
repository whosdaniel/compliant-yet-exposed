"""amendment1_countonly.py -- the count-only re-run of amendment 1 (revision/
prereg_amendment1_count_only.md): every in-scope script with CYE_FEATURES=count (the downlink observer
sees the per-window record count only), writing into results_countonly/. Run it after
amendment1_regression.py passes. E8 (pilot2s_scale.py, about 2.6 h on 18 cores) and its analysis
(pilot2t_scale_analysis.py) run last; --skip-e8 leaves them out.
Run: python amendment1_countonly.py [--skip-e8]
"""
import hashlib, json, os, platform, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_countonly")
AMENDMENT = os.path.join(HERE, "..", "revision", "prereg_amendment1_count_only.md")
PY = sys.executable
FAST = ["pilot2_command_channel.py", "pilot2b_correlation.py", "pilot2c_sensitivity.py", "pilot2d_within_pool.py",
        "pilot2e_boundary.py", "pilot2f_nuisance.py", "pilot2h_disaggregation.py", "pilot2i_metrics.py",
        "pilot2j_wsweep.py", "pilot2k_ari_curves.py", "pilot2m_psweep.py", "pilot2n_drift.py",
        "pilot2o_fig_ari.py", "pilot2r_unknown_k.py"]
E8 = ["pilot2s_scale.py", "pilot2t_scale_analysis.py"]


def run(script, log_dir):
    env = dict(os.environ, CYE_FEATURES="count", CYE_RESULTS=OUT)
    t0 = time.time()
    with open(os.path.join(log_dir, script.replace(".py", ".log")), "w") as log:
        rc = subprocess.run([PY, script], cwd=HERE, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    return script, rc, round(time.time() - t0, 1)


def main():
    log_dir = os.path.join(OUT, "logs"); os.makedirs(log_dir, exist_ok=True)
    import numpy, scipy, sklearn
    man_p = os.path.join(OUT, "run_manifest.json")
    man = json.load(open(man_p)) if os.path.exists(man_p) else {}
    man.update({"features": "count", "amendment_sha256": hashlib.sha256(open(AMENDMENT, "rb").read()).hexdigest(),
                "python": platform.python_version(), "numpy": numpy.__version__, "scipy": scipy.__version__,
                "sklearn": sklearn.__version__, "machine": f"{platform.machine()} {os.cpu_count()} cores"})
    man.setdefault("runs", {})

    def record(script, rc, sec):
        man["runs"][script] = {"rc": rc, "seconds": sec, "finished": time.strftime("%Y-%m-%d %H:%M:%S %z")}
        json.dump(man, open(man_p, "w"), indent=2)
        print(f"{script:<28} rc={rc} {sec:>8.1f}s", flush=True)

    with ThreadPoolExecutor(max_workers=6) as ex:
        for res in ex.map(lambda s: run(s, log_dir), FAST):
            record(*res)
    if "--skip-e8" not in sys.argv:
        for script in E8:
            res = run(script, log_dir)
            record(*res)
            if res[1] != 0:
                break
    bad = [s for s, r in man["runs"].items() if r["rc"] != 0]
    print("done;", "all scripts exited 0" if not bad else f"non-zero exit: {bad}")


if __name__ == "__main__":
    main()
