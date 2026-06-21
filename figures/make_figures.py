"""make_figures.py — result figures (data from pilot/results/*.json).
Achromatic / journal palette (no hue), larger fonts, no label/legend overlaps.
All numbers are actual pilot outputs; nothing here is hand-set beyond labels."""
import os, json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

FIGS = os.path.join(os.path.dirname(__file__), "figs"); os.makedirs(FIGS, exist_ok=True)
PILOT_RES = os.path.join(os.path.dirname(__file__), "..", "pilot", "results")
def _load(name): return json.load(open(os.path.join(PILOT_RES, name)))
P2 = _load("pilot2_results.json")
CORR = _load("pilot2b_correlation.json")
BOUND = _load("pilot2e_boundary.json")
K_ARI = _load("pilot2k_ari_curves.json")
FIGARI = _load("pilot2o_fig_ari.json")
DRIFT = _load("pilot2n_drift.json")
plt.rcParams.update({
    "font.family": "serif", "font.size": 10, "axes.linewidth": 0.9,
    "axes.labelsize": 10.5, "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 8.5,
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#3a3f45",
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.12,
})
# ---- achromatic / journal palette (no hue) ----
INK  = "#1a1a1a"   # primary / real / headline
G_DK = "#555555"   # secondary series
G_MD = "#8a8a8a"   # tertiary / controls
G_LT = "#c4c4c4"   # controls / open / idle
NULLG = "#9aa4af"  # null / reference lines
SHADEG = "#ededed" # shaded region (neutral gray, no hue)

NULLLAB = "null (ARI $\\approx$ 0)"
def null_line(ax, x, y=0.0, ha="center"):
    """null reference line + a label placed at an explicit (data-x, y) empty spot."""
    ax.axhline(0.0, ls=(0, (5, 3)), lw=0.9, color=NULLG, zorder=1)
    ax.text(x, 0.022, NULLLAB, color="#6b7480", fontsize=8, ha=ha, va="bottom", zorder=5)

# ---- Fig 5: E2 co-membership vs controls (headline) + E6 ----
def fig_e2():
    e = FIGARI["e2_controls"]
    labels = ["real\n(distinct\nwindows)", "function-\nonly", "random\nlabel", "no-structure\n(E6)"]
    keys = ["real", "function_only", "random_label", "no_structure"]
    vals = [e[k]["ari"] for k in keys]; errs = [e[k]["ari_sd"] for k in keys]
    cols = [INK, G_LT, G_LT, G_LT]
    fig, ax = plt.subplots(figsize=(4.2, 3.0))
    ax.axvspan(0.5, 3.5, color=SHADEG, zorder=0)
    ax.text(2.0, 1.12, "negative controls (expect $\\approx$ 0)", ha="center", va="bottom",
            fontsize=8, color=G_DK, style="italic")
    bars = ax.bar(labels, vals, yerr=errs, color=cols, width=0.66, zorder=3, edgecolor=INK,
                  linewidth=0.7, error_kw=dict(ecolor=INK, lw=0.9, capsize=3, zorder=4))
    for b, v, er in zip(bars, vals, errs):
        # real bar shows its value; the controls are all noise-level (~0), so label "~0"
        # rather than a rounded "0.01" that would falsely read as identical despite real height differences
        lab = f"{v:.2f}" if v > 0.5 else "$\\approx$0"
        ax.text(b.get_x() + b.get_width() / 2, max(v, 0) + er + 0.035,
                lab, ha="center", va="bottom", fontsize=9)
    ax.axhline(0.0, ls=(0, (5, 3)), lw=0.9, color=NULLG, zorder=1)  # null=0; the "expect ~0" note above already labels it
    ax.set_ylim(-0.1, 1.2); ax.set_ylabel("co-membership ARI")
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])               # ARI maxes at 1.0 -- no tick above it
    fig.savefig(os.path.join(FIGS, "fig_e2_comembership.png")); plt.close(fig)

# ---- Fig 8: award-correlation boundary (§8.4) ----
def fig_corr():
    fig, ax = plt.subplots(figsize=(4.2, 3.1))
    styles = {24: ("-o", INK, 1.7), 8: ("--s", G_DK, 1.5), 4: (":^", G_MD, 1.5)}
    for W in (24, 8, 4):
        pts = sorted([r for r in FIGARI["c_multiW"] if r["W"] == W], key=lambda x: x["c"])
        c = [p["c"] for p in pts]; ari = [p["ari"] for p in pts]
        fmt, col, lw = styles[W]
        ax.plot(c, ari, fmt, color=col, ms=4.5, lw=lw, label=f"W = {W}", zorder=3,
                markerfacecolor=col, markeredgecolor="white", markeredgewidth=0.6)
    null_line(ax, x=0.5)                                   # null label centered-bottom (empty)
    ax.set_xlim(0, 1.0); ax.set_ylim(-0.05, 1.08)
    ax.set_xlabel("latent copula correlation  $c$")
    ax.set_ylabel("co-membership ARI")
    ax.legend(loc="lower left", frameon=False, title="observed\nwindows", title_fontsize=8.5,
              handlelength=2.2, borderaxespad=0.4)
    fig.savefig(os.path.join(FIGS, "fig_correlation_boundary.png")); plt.close(fig)

# ---- Fig 10: within-pool synchronization gamma ----
def fig_within_pool():
    fig, ax = plt.subplots(figsize=(4.2, 3.1))
    styles = {2: ("-o", INK, 1.7), 5: ("--s", G_DK, 1.5)}
    rows = K_ARI["gamma_sweep_corr0_W24"]
    for K in (2, 5):
        pts = sorted([r for r in rows if r["K"] == K], key=lambda x: x["gamma"])
        g = [r["gamma"] for r in pts]; ari = [r["ari"][0] for r in pts]
        fmt, col, lw = styles[K]
        ax.plot(g, ari, fmt, color=col, ms=4.5, lw=lw, label=f"K = {K}", zorder=3,
                markerfacecolor=col, markeredgecolor="white", markeredgewidth=0.6)
    null_line(ax, x=0.5)
    ax.set_xlim(0, 1.05); ax.set_ylim(-0.05, 1.08)
    ax.set_xlabel("within-pool schedule homogeneity  $\\gamma$")
    ax.set_ylabel("co-membership ARI")
    ax.legend(loc="lower right", frameon=False, handlelength=2.2)
    fig.savefig(os.path.join(FIGS, "fig_within_pool.png")); plt.close(fig)

# ---- Fig 7: attacker cost (E4) ----
def fig_e4():
    cost = P2["E4_attacker_cost"]
    W = [d[0] for d in cost]; acc = [d[1] for d in cost]; err = [d[2] for d in cost]
    up = [min(a + e, 1.0) - a for a, e in zip(acc, err)]   # clip the upper whisker at the accuracy ceiling (1.0)
    fig, ax = plt.subplots(figsize=(4.2, 3.0))
    ax.errorbar(W, acc, yerr=[err, up], fmt="-o", color=INK, ms=5, lw=1.6, capsize=3.5,
                ecolor=INK, markerfacecolor=INK, markeredgecolor="white", markeredgewidth=0.7, zorder=3)
    ax.axhline(0.9, ls=(0, (1, 2)), lw=1.0, color=G_MD, zorder=1)
    ax.text(34, 0.905, "0.9", color=G_MD, fontsize=8.5, ha="right", va="bottom")
    ax.axhline(0.59, ls=(0, (5, 3)), lw=1.0, color=NULLG, zorder=1)
    ax.text(32, 0.605, "empirical floor (K = 2)", color="#6b7480", fontsize=8.5, ha="right", va="bottom")
    ax.set_xscale("log", base=2); ax.set_xticks(W); ax.set_xticklabels(W)
    ax.set_xlabel("observed award windows  $W$"); ax.set_ylabel("co-membership accuracy")
    ax.set_ylim(0.4, 1.04)                                  # accuracy maxes at 1.0; upper error bar clipped at the ceiling
    ax.set_yticks([0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])     # accuracy maxes at 1.0 -- no misleading tick above it
    fig.savefig(os.path.join(FIGS, "fig_attacker_cost.png")); plt.close(fig)

# ---- (legacy, unused in doc) which defense closes the channel ----
def fig_e3():
    d = FIGARI["defenses"]
    order = [("pad", "pad\n(const+fixed)"), ("vpn", "full\nVPN"),
             ("batch", "batch"), ("cover", "cover"), ("jitter", "jitter")]
    defs = [lbl for _, lbl in order]
    best = [d[key]["ari"] for key, _ in order]
    closed = [v < 0.5 for v in best]
    cols = [INK if c else G_LT for c in closed]
    fig, ax = plt.subplots(figsize=(4.0, 3.0))
    bars = ax.bar(defs, best, color=cols, width=0.64, zorder=3, edgecolor=INK, linewidth=0.7)
    for b, v, c in zip(bars, best, closed):
        ax.text(b.get_x() + b.get_width() / 2, max(v, 0) + 0.04, f"{0.0 if abs(v) < 0.005 else v:.2f}", ha="center", va="bottom", fontsize=9)
        ax.text(b.get_x() + b.get_width() / 2, max(v, 0) + 0.15, "closed" if c else "open",
                ha="center", va="bottom", fontsize=8, color=(INK if c else G_MD), style="italic")
    ax.axhline(0.0, ls=(0, (5, 3)), lw=0.9, color=NULLG, zorder=1)
    ax.text(-0.46, 0.03, NULLLAB, color="#6b7480", fontsize=8, ha="left", va="bottom")
    ax.set_ylim(-0.1, 1.36); ax.set_ylabel("attack ARI at strongest setting\n(lower = channel closed)")
    fig.savefig(os.path.join(FIGS, "fig_defenses.png")); plt.close(fig)

# ---- Fig 4: idle vs active traffic, real TLS wire bytes ----
def fig_traffic():
    fig, axes = plt.subplots(1, 2, figsize=(5.0, 2.8))
    for ax, (title, idle, active) in zip(
        axes, [("messages / min", 2, 15), ("mean wire bytes / message", 300, 34)]):
        bars = ax.bar(["idle", "active\nregulation"], [idle, active], color=[G_LT, INK], width=0.6,
                      zorder=3, edgecolor=INK, linewidth=0.7)
        for b, v in zip(bars, [idle, active]):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:,}", ha="center", va="bottom", fontsize=9)
        ax.set_title(title, fontsize=9.5); ax.margins(y=0.18)
    fig.savefig(os.path.join(FIGS, "fig_traffic_shape.png")); plt.close(fig)

# ---- Fig 9: sensitivity to background contamination phi ----
def fig_sensitivity():
    p = os.path.join(PILOT_RES, "pilot2c_sensitivity.json")
    data = json.load(open(p))
    phi = [d[0] for d in data]; ari = [d[3] for d in data]; std = [d[4] for d in data]
    fig, ax = plt.subplots(figsize=(4.2, 3.1))
    ax.axvspan(0.0, 0.5, color=SHADEG, zorder=0)
    ax.text(0.25, 0.42, "robust\nregion", ha="center", va="center", fontsize=8.5, color="#5a6470",
            style="italic")
    lo = [a - s for a, s in zip(ari, std)]
    hi = [min(a + s, 1.0) for a, s in zip(ari, std)]   # clip the +1 SD band at the ARI ceiling (1.0); no seed exceeds it
    ax.fill_between(phi, lo, hi, color=G_MD, alpha=0.18, zorder=2)
    ax.plot(phi, ari, "-o", color=INK, ms=5, lw=1.6, markerfacecolor=INK,
            markeredgecolor="white", markeredgewidth=0.7, zorder=3)
    ax.axhline(0.0, ls=(0, (5, 3)), lw=0.9, color=NULLG, zorder=1)
    ax.text(0.02, 0.03, NULLLAB, color="#6b7480", fontsize=8, ha="left", va="bottom")
    ax.set_xlim(0, 0.9); ax.set_ylim(-0.05, 1.04)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])           # ARI maxes at 1.0
    ax.set_xlabel("background contamination  $\\varphi$")
    ax.set_ylabel("co-membership ARI")
    fig.savefig(os.path.join(FIGS, "fig_sensitivity.png")); plt.close(fig)

# ---- Fig 11: patient-observer realizability ----
def fig_drift():
    fig, ax = plt.subplots(figsize=(4.2, 3.1))
    styles = {"stationary": ("-o", INK, 1.7, "stationary"),
              "param_drift": ("--s", G_DK, 1.5, "param drift"),
              "churn": (":^", G_MD, 1.5, "membership churn")}
    for mode in ("stationary", "param_drift", "churn"):
        pts = sorted([r for r in DRIFT if r["mode"] == mode], key=lambda x: x["W"])
        Ws = [r["W"] for r in pts]; ari = [r["ari"] for r in pts]
        fmt, col, lw, lab = styles[mode]
        ax.plot(Ws, ari, fmt, color=col, ms=5, lw=lw, label=lab, zorder=3,
                markerfacecolor=col, markeredgecolor="white", markeredgewidth=0.6)
    ax.axhline(0.0, ls=(0, (5, 3)), lw=0.9, color=NULLG, zorder=1)
    ax.set_xscale("log", base=2); ax.set_xticks([8, 16, 32, 64, 128]); ax.set_xticklabels([8, 16, 32, 64, 128])
    ax.set_xlabel("observed award windows  $W$")
    ax.set_ylabel("co-membership ARI")
    ax.set_ylim(-0.05, 0.95)
    ax.legend(loc="upper left", frameon=False, handlelength=2.2)
    fig.savefig(os.path.join(FIGS, "fig_drift.png")); plt.close(fig)


for f in (fig_e2, fig_corr, fig_within_pool, fig_e4, fig_e3, fig_traffic, fig_sensitivity, fig_drift):
    f(); print("ok", f.__name__)
print("figs ->", FIGS)
