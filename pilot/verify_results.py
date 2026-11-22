"""verify_results.py -- re-run every fast experiment for both observers into a scratch folder and compare each result field
with the stored result files, exactly (only wall-clock and memory fields are exempt). The stored files are only read.
  downlink observer, the paper's results (CYE_FEATURES=count) -> results_countonly/
  bidirectional variant (CYE_FEATURES unset = count+size)     -> results/
Also checked: the background sweep with per-DER standardization (CYE_BG_NORM=der) and the E8 analysis, recomputed from
the stored E8 per-run records. The E8 runs themselves are checked by pilot2s_verify.py (exact re-runs of a fixed sample).
Not compared: the loopback TLS scripts and pilot2p_hil.py, which use real sockets and wall-clock timing.
About one minute on a laptop.  Run: python verify_results.py <scratch_dir>
"""
import json, os, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from amendment1_regression import diff, is_timing

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
COMMON = ["pilot2_command_channel.py", "pilot2b_correlation.py", "pilot2c_sensitivity.py", "pilot2d_within_pool.py",
          "pilot2e_boundary.py", "pilot2f_nuisance.py", "pilot2g_mechanism.py", "pilot2h_disaggregation.py",
          "pilot2i_metrics.py", "pilot2j_wsweep.py", "pilot2k_ari_curves.py", "pilot2m_psweep.py", "pilot2n_drift.py",
          "pilot2o_fig_ari.py", "pilot2r_unknown_k.py"]
MODES = {"count": ("results_countonly", COMMON),
         "count+size": ("results", COMMON + ["pilot2L_direction.py", "pilot2q_defense_factorial.py"])}
OUT = {"pilot2_command_channel.py": "pilot2_results.json"}


def run(script, mode, dest, extra=None):
    env = dict(os.environ, CYE_RESULTS=dest, **(extra or {}))
    env.pop("CYE_FEATURES", None)
    if mode == "count":
        env["CYE_FEATURES"] = "count"
    p = subprocess.run([PY, script], cwd=HERE, env=env, capture_output=True, text=True)
    return script, p.returncode, p.stdout[-2000:] + p.stderr[-2000:]


def main():
    scratch = os.path.abspath(sys.argv[1])
    bad = 0
    for mode, (stored_dir, scripts) in MODES.items():
        dest = os.path.join(scratch, stored_dir)
        os.makedirs(dest, exist_ok=True)
        jobs = [(s, None) for s in scripts] + [("pilot2c_sensitivity.py", {"CYE_BG_NORM": "der"})]
        with ThreadPoolExecutor(max_workers=6) as ex:
            for script, rc, tail in ex.map(lambda j: run(j[0], mode, dest, j[1]), jobs):
                if rc != 0:
                    print(f"[{mode}] {script} exited {rc}\n{tail}"); bad += 1
        for f in ("pilot2s_scale.jsonl", "pilot2s_scale.json"):            # E8 analysis from the stored E8 runs
            shutil.copy2(os.path.join(HERE, stored_dir, f), os.path.join(dest, f))
        _, rc, tail = run("pilot2t_scale_analysis.py", mode, dest)
        if rc != 0:
            print(f"[{mode}] pilot2t_scale_analysis.py exited {rc}\n{tail}"); bad += 1
        names = [OUT.get(s, s.replace(".py", ".json")) for s in scripts]
        names += ["pilot2c_sensitivity_perder.json", "pilot2t_scale_analysis.json"]
        for name in names:
            new_p, old_p = os.path.join(dest, name), os.path.join(HERE, stored_dir, name)
            if not os.path.exists(new_p):
                print(f"[{mode}] {name}: not produced"); bad += 1; continue
            d = [x for x in diff(json.load(open(old_p)), json.load(open(new_p))) if not is_timing(x[0])]
            print(f"[{mode:<10}] {stored_dir}/{name:<34} {'MATCH' if not d else 'MISMATCH ' + str(d[:3])}")
            bad += bool(d)
    print("overall:", "PASS" if not bad else f"FAIL ({bad})")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
