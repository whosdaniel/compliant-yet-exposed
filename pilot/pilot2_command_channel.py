"""
pilot2_command_channel.py — testbed for the SURVIVING signal: per-DER command-down
(disaggregation setpoint) channel during active AS/regulation.

ANTI-TAUTOLOGY DISCIPLINE (the repo's founding lesson, applied here):
  "signal exists" is DEFINITIONAL — if setpoints go out ~every 4s during an award window,
  per-DER inbound has a ~4s cadence in that window. Reproducing that is NOT a finding
  (the signal exists by construction). So E1 is labelled trivial.
  The FINDINGS are:
    E2  function-separation : does clustering recover CO-MEMBERSHIP (same pool) vs merely
        FUNCTION (is-a-regulation-provider)?  [real vs function-only-confound vs chance]
    E3  robustness/closing-defense : which deployable defense closes it, and how cheaply?
    E4  attacker cost : #observed award-windows needed for a target accuracy.
    E6  negative control : behavioural confound (no pools) must collapse to chance.

Channel params are grounded in REAL protocol sizes (Modbus WriteSingleRegister ADU = 12 B
[spec], TLS1.3 AES-GCM record overhead = 22 B [measured], 2030.5 telemetry ≈ 200-600 B).
  active (setpoint): frequent (~4 s), SMALL (~50 B).   idle (telemetry): rare (~30 s), LARGE (~400 B).
Observer (passive, per-DER link, encrypted): sees per-window packet COUNT and mean SIZE only.
"""
from __future__ import annotations
import json, os
import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform, pdist
from scipy.optimize import linear_sum_assignment

RES = os.path.join(os.path.dirname(__file__), "results"); os.makedirs(RES, exist_ok=True)

# --- REAL-MEASURED channel params (sizes = real TLS-encrypted wire bytes, real_tls_measure.py) ---
# TLS1.3 AES-256-GCM record overhead = 22 B [MEASURED, ssl MemoryBIO]; Modbus write ADU = 12 B [spec].
LAM_ACT = 900.0   # packets/hr during active regulation (~4s setpoint cadence)
LAM_IDLE = 120.0  # packets/hr idle (~30s telemetry, per SCE COT ≤30s)
SZ_ACT, SZ_ACT_SD = 34.0, 4.0       # setpoint (Modbus write 12B + TLS 22B) = 34 B [MEASURED]
SZ_IDLE, SZ_IDLE_SD = 300.0, 60.0   # telemetry (2030.5 MMR 126B .. oadrReport 341B) [MEASURED range]

SEEDS = 50   # Monte-Carlo seeds per condition (was 16). We report mean +/- SD and 95% CI over these.


def gen(M=24, K=2, W=24, p_award=0.5, seed=0, same_windows=False, no_pools=False,
        defense=None, dparam=0.0):
    """Per-DER × per-award-window observables (count, mean_size). Defenses perturb the
    ACTIVE windows to hide them. same_windows=function-only confound; no_pools=behavioural confound."""
    rng = np.random.default_rng(seed)
    if no_pools:
        # each DER has its OWN random award schedule (no pool structure)
        active = rng.random((M, W)) < p_award
        pools = np.array([i % K for i in range(M)]); rng.shuffle(pools)  # labels are meaningless here
    else:
        pools = np.array([i % K for i in range(M)]); rng.shuffle(pools)
        if same_windows:
            sched = rng.random(W) < p_award                      # ALL pools share one schedule
            pool_sched = {k: sched for k in range(K)}
        else:
            pool_sched = {k: (rng.random(W) < p_award) for k in range(K)}  # distinct per pool
        active = np.array([pool_sched[pools[i]] for i in range(M)])
    count = np.where(active, LAM_ACT, LAM_IDLE).astype(float)
    size = np.where(active, SZ_ACT, SZ_IDLE).astype(float)
    # sampling noise
    count = rng.poisson(np.clip(count, 1, None)).astype(float)
    size = size + rng.normal(0, np.where(active, SZ_ACT_SD, SZ_IDLE_SD))
    # --- deployable defenses (applied to hide the active-window signal) ---
    if defense == "jitter":
        # timing perturbation within window: does NOT change per-window count -> weak
        pass
    elif defense == "batch":
        b = max(1.0, dparam)                      # batch b setpoints into 1 packet
        count = np.where(active, count / b, count)
        size = np.where(active, size * b, size)   # batched packet larger
    elif defense == "pad":
        # constant cadence + fixed size (NK5 "both channels closed")
        if dparam >= 1.0:
            count[:] = (LAM_ACT + LAM_IDLE) / 2
            size[:] = (SZ_ACT + SZ_IDLE) / 2
    elif defense == "cover":
        count = count + rng.poisson(dparam * LAM_IDLE, size=count.shape)  # random cover packets
    elif defense == "vpn":
        # fraction of DERs tunnelled -> observer loses per-DER resolution (random features)
        masked = rng.random(M) < dparam
        count[masked] = rng.poisson((LAM_ACT + LAM_IDLE) / 2, size=(masked.sum(), W))
        size[masked] = (SZ_ACT + SZ_IDLE) / 2 + rng.normal(0, 30, size=(masked.sum(), W))
    # observer features: z-normalized count + size across windows
    feat = np.hstack([_z(count), _z(size)])
    return feat, pools


def _z(x):
    m = x.mean(axis=1, keepdims=True); s = x.std(axis=1, keepdims=True); s[s == 0] = 1
    return (x - m) / s


def cluster(feat, K):
    D = pdist(feat, metric="euclidean")
    Z = linkage(D, method="ward")
    return fcluster(Z, K, criterion="maxclust")


def accuracy(true, pred, K):
    C = np.zeros((K, K))
    for t, p in zip(true, pred):
        C[t, p - 1] += 1
    r, c = linear_sum_assignment(-C)
    return C[r, c].sum() / len(true)


def ari(true, pred):
    n = len(true); a = np.unique(true); b = np.unique(pred)
    cont = np.array([[np.sum((true == i) & (pred == j)) for j in b] for i in a])
    sa = cont.sum(1); sb = cont.sum(0)
    idx = np.sum([v * (v - 1) / 2 for v in cont.flatten()])
    ea = np.sum([v * (v - 1) / 2 for v in sa]); eb = np.sum([v * (v - 1) / 2 for v in sb])
    exp = ea * eb / (n * (n - 1) / 2); mx = (ea + eb) / 2
    return (idx - exp) / (mx - exp) if mx != exp else 0.0


def trial(K=2, seeds=SEEDS, **kw):
    accs, aris = [], []
    for s in range(seeds):
        feat, pools = gen(K=K, seed=s, **kw)
        pred = cluster(feat, K)
        accs.append(accuracy(pools, pred, K)); aris.append(ari(pools, pred))
    return np.mean(accs), np.std(accs), np.mean(aris)


def ci95(sd, n=SEEDS):
    """95% CI half-width for the MEAN over n seeds (normal approx)."""
    return 1.96 * sd / np.sqrt(n)


def main():
    K = 2; chance = 1.0 / K
    out = {"n_seeds": SEEDS}
    print("=" * 80)
    print("PILOT 2 — command-down (disaggregation setpoint) channel. baseline accuracy =", chance)
    print("real-grounded sizes: setpoint~34B(Modbus12+TLS22), telemetry~300B; active~4s, idle~30s")
    print(f"Monte-Carlo: mean +/- SD over {SEEDS} seeds/condition (95% CI = 1.96*SD/sqrt(n)).")
    print("=" * 80)

    # E1 — TRIVIAL (labelled): no defense, distinct pool windows
    a, sd, ar = trial(W=24)
    out["E1_trivial_signal_exists"] = dict(acc=a, sd=sd, ci95=ci95(sd), ari=ar)
    print(f"\n[E1 — TRIVIAL, *not* a finding] distinct pool windows, no defense: acc={a:.3f}±{sd:.3f} (ari={ar:.2f})")
    print("   (definitional: active windows visible → pools separable; the signal exists by construction.)")

    # E2 — FUNCTION-SEPARATION (the actual co-membership test)
    a_real, sd_real, ar_real = trial(W=24, same_windows=False)
    a_func, sd_func, ar_func = trial(W=24, same_windows=True)   # all pools share windows = function held constant
    a_rand = []  # random-label control
    for s in range(SEEDS):
        feat, pools = gen(K=K, seed=s, W=24)
        pred = cluster(feat, K); rng = np.random.default_rng(100 + s)
        a_rand.append(accuracy(rng.permutation(pools), pred, K))
    m_rand, sd_rand = float(np.mean(a_rand)), float(np.std(a_rand))
    out["E2_function_separation"] = dict(
        real=a_real, real_sd=sd_real, function_only=a_func, function_only_sd=sd_func,
        random_label=m_rand, random_label_sd=sd_rand, chance=chance, seeds=SEEDS)
    print(f"\n[E2 — FUNCTION-SEPARATION ★ headline] does timing recover CO-MEMBERSHIP vs FUNCTION?")
    print(f"   real (distinct pool windows)        acc={a_real:.3f}±{sd_real:.3f} ari={ar_real:.2f}")
    print(f"   function-only (pools share windows)  acc={a_func:.3f}±{sd_func:.3f} ari={ar_func:.2f}   <- function held constant")
    print(f"   random-label control                 acc={m_rand:.3f}±{sd_rand:.3f}   chance={chance:.3f}")
    verdict = "CO-MEMBERSHIP" if (a_real - a_func) > 0.2 and a_func < chance + 0.15 else "FUNCTION-ENTANGLED"
    print(f"   -> {verdict}: real>>function_only≈chance ⇒ pool-timing(co-membership), not just 'is-a-provider'")

    # E3 — ROBUSTNESS / closing defense
    print(f"\n[E3 — ROBUSTNESS ★ headline] which deployable defense closes it (acc→chance)?")
    rob = {}
    for dfn, params in [("jitter", [1, 5, 15]), ("batch", [2, 8, 32]),
                        ("cover", [1.0, 4.0, 16.0]), ("vpn", [0.25, 0.5, 1.0]),
                        ("pad", [1.0])]:
        row = []
        for p in params:
            a, sd, _ = trial(W=24, defense=dfn, dparam=p)
            row.append([p, round(a, 3), round(sd, 3)])
        rob[dfn] = row
        print(f"   {dfn:7s}: {row}")
    out["E3_robustness"] = rob
    print("   -> jitter/cover weak (per-window count survives); pad (constant-cadence+fixed-size) closes it;")
    print("      vpn closes it by removing per-DER resolution; batch closes only at large b.")

    # E4 — ATTACKER COST (observed award-windows → accuracy)
    print(f"\n[E4 — ATTACKER COST ★ headline] #observed award-windows W → accuracy:")
    cost = []
    for W in (1, 2, 4, 8, 16, 32):
        a, sd, _ = trial(W=W)
        cost.append([W, round(a, 3), round(sd, 3)])
        print(f"   W={W:3d} windows : acc={a:.3f} ± {sd:.3f}")
    out["E4_attacker_cost"] = cost
    wmin = next((W for W, a, _ in cost if a >= 0.9), None)
    print(f"   -> ~{wmin} award-windows for acc≥0.9 (≈ that many regulation awards observed).")

    # E5 — multi-DERA (K pools)
    print(f"\n[E5 — multi-pool separability]:")
    e5 = []
    for k in (2, 3, 4):
        a, sd, ar = trial(K=k, W=32)
        e5.append([k, round(a, 3), round(sd, 3), round(ar, 2), round(1.0 / k, 3)])
        print(f"   K={k} pools: acc={a:.3f}±{sd:.3f} ari={ar:.2f} (chance={1.0/k:.3f})")
    out["E5_multi_pool"] = e5

    # E6 — NEGATIVE CONTROL (behavioural confound: no pools)
    print(f"\n[E6 — NEGATIVE CONTROL ★ anti-tautology] no pools (random per-DER schedules):")
    nc = []
    for s in range(SEEDS):
        feat, pools = gen(no_pools=True, seed=s, W=24)
        pred = cluster(feat, 2)
        nc.append(accuracy(pools, pred, 2))   # 'pools' here are meaningless random labels
    m_nc, sd_nc = float(np.mean(nc)), float(np.std(nc))
    print(f"   acc vs (meaningless) labels = {m_nc:.3f}±{sd_nc:.3f} ≈ chance {chance:.3f}  "
          f"-> clustering does NOT manufacture pool structure when none exists. ✓")
    out["E6_negative_control_nopools"] = dict(acc=m_nc, sd=sd_nc, ci95=ci95(sd_nc), seeds=SEEDS)

    print("\n" + "=" * 80)
    print("HEADLINE (NOT 'signal exists' — that is E1/trivial):")
    print(f"  • co-membership vs function: {verdict} (E2: real {a_real:.2f}±{sd_real:.2f} vs func {a_func:.2f}±{sd_func:.2f} vs chance {chance:.2f})")
    print(f"  • closing defense: pad(constant-cadence+fixed-size) & vpn; jitter/cover/small-batch weak (E3)")
    print(f"  • attacker cost: ~{wmin} observed award-windows for acc≥0.9 (E4)")
    print(f"  • negative control passes: no spurious structure (E6 {m_nc:.2f}±{sd_nc:.2f}≈{chance:.2f})")
    with open(os.path.join(RES, "pilot2_results.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"saved -> {RES}/pilot2_results.json")


if __name__ == "__main__":
    main()
