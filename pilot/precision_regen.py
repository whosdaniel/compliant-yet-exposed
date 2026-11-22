"""precision_regen.py -- regenerate the result files at six-decimal precision (revision R1, 2026-11-15).

The scripts used to round stored means and SDs to two to four decimals, so a value shown to two decimals in the paper
was sometimes rounded twice (for example 0.314977 stored as 0.315 and shown as 0.32). The rounding calls now keep six
decimals. This script re-runs every in-scope script for both observers into a scratch directory and checks that each
new value lies inside the rounding interval of the stored value (|new - old| <= half a unit in the old value's last
decimal; integers must match exactly). Only if every file passes does `--install` copy the new files over the stored
ones. Nothing else changes: generators, seeds, grids, estimators. E8 per-run records are not re-run.
Run: python precision_regen.py <scratch_dir> [--install]
"""
import json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
FAST = ["pilot2_command_channel.py", "pilot2b_correlation.py", "pilot2c_sensitivity.py", "pilot2d_within_pool.py",
        "pilot2e_boundary.py", "pilot2f_nuisance.py", "pilot2g_mechanism.py", "pilot2h_disaggregation.py",
        "pilot2i_metrics.py", "pilot2j_wsweep.py", "pilot2k_ari_curves.py", "pilot2m_psweep.py", "pilot2n_drift.py",
        "pilot2o_fig_ari.py", "pilot2r_unknown_k.py"]
OUTPUTS = {"pilot2_command_channel.py": "pilot2_results.json", "pilot2r_unknown_k.py": "pilot2r_unknown_k.json"}
MODES = {"count": "results_countonly", "count+size": "results"}


def out_name(script):
    return OUTPUTS.get(script, script.replace(".py", ".json"))


def decimals(v):
    s = repr(float(v))
    return len(s.split(".")[1]) if "." in s and "e" not in s else 6


def check(old, new, path=""):
    """Paths where new is outside the rounding interval of old."""
    if isinstance(old, dict):
        bad = [] if set(old) == set(new) else [(path + "/<keys>", sorted(old), sorted(new))]
        return bad + [b for k in old if k in new for b in check(old[k], new[k], f"{path}/{k}")]
    if isinstance(old, list):
        if not isinstance(new, list) or len(old) != len(new):
            return [(path + "/<len>", old, new)]
        return [b for i, (x, y) in enumerate(zip(old, new)) for b in check(x, y, f"{path}[{i}]")]
    if isinstance(old, bool) or isinstance(old, str) or old is None:
        return [] if old == new else [(path, old, new)]
    if isinstance(old, int) and isinstance(new, int):
        return [] if old == new else [(path, old, new)]
    tol = 0.5 * 10 ** (-max(decimals(old), 2)) + 1e-12
    return [] if abs(float(new) - float(old)) <= tol else [(path, old, new)]


def main():
    scratch = os.path.abspath(sys.argv[1]); install = "--install" in sys.argv
    report, bad_total = {}, 0
    for feat, stored in MODES.items():
        d = os.path.join(scratch, stored); os.makedirs(d, exist_ok=True)
        env = dict(os.environ, CYE_RESULTS=d, CYE_FEATURES=feat)
        for s in FAST:
            rc = subprocess.run([PY, s], cwd=HERE, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT).returncode
            if rc:
                sys.exit(f"{s} ({feat}) failed with exit {rc}")
        for f in ("pilot2s_scale.jsonl", "pilot2s_scale.json"):          # E8 analysis reads the stored per-run records
            shutil.copy2(os.path.join(HERE, stored, f), os.path.join(d, f))
        subprocess.run([PY, "pilot2t_scale_analysis.py"], cwd=HERE, env=env, stdout=subprocess.DEVNULL, check=True)
        for s in FAST + ["pilot2t_scale_analysis.py"]:
            name = out_name(s)
            bad = check(json.load(open(os.path.join(HERE, stored, name))), json.load(open(os.path.join(d, name))))
            report[f"{stored}/{name}"] = {"outside_interval": len(bad), "examples": [list(map(str, b)) for b in bad[:5]]}
            bad_total += len(bad)
            print(f"{stored}/{name:<30} {'OK' if not bad else f'{len(bad)} OUTSIDE'}")
    json.dump({"overall": "PASS" if not bad_total else f"FAIL ({bad_total})", "files": report},
              open(os.path.join(scratch, "precision_regen_report.json"), "w"), indent=2)
    print("overall:", "PASS" if not bad_total else f"FAIL ({bad_total})")
    if install and not bad_total:
        for feat, stored in MODES.items():
            for s in FAST + ["pilot2t_scale_analysis.py"]:
                shutil.copy2(os.path.join(scratch, stored, out_name(s)), os.path.join(HERE, stored, out_name(s)))
        print("installed six-decimal result files into", ", ".join(MODES.values()))


if __name__ == "__main__":
    main()
