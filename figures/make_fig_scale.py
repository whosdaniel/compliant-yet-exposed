"""make_fig_scale.py — E8 scale figure (revision R1), achromatic journal style, sized for the page width.
Three panels under adverse timing (c = 0.5, γ = 0.6), computed from the per-run E8 records (pilot2s_scale.jsonl) so
every point is a mean with a ±1 SD band; nothing is hand-set beyond labels.
  (a) adding members: ARI vs DERs in the aggregation M with the pool count fixed (K = 2, 16, 64), true K,
      W = 96 (solid) and W = 24 (dashed)
  (b) adding pools: ARI vs the number of pools K at 768 DERs per pool (M = 768 K): true K at W = 96 and W = 24,
      and the silhouette-estimated K at W = 24
  (c) estimating K: ARI vs observed windows W at M = 12,288 (the largest M with the full W grid), true K (solid,
      filled, with bands) vs estimated K (dotted, open), K = 2, 16, 64
One legend above the panels gives the pool-count shades of (a) and (c); each panel's own legend gives its line styles.
Seeds per configuration: 20 up to 6,144 DERs, 10 at 12,288, 5 above.
Reads pilot/results_countonly (the downlink observer) unless CYE_RESULTS names another results directory.
Run:  python make_fig_scale.py
"""
import json, os
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.environ.get("CYE_RESULTS") or os.path.join(HERE, "..", "pilot", "results_countonly")
OUT = os.path.join(HERE, "figs", "fig_scale.png")
plt.rcParams.update({
    "font.family": "serif", "font.size": 8.5, "axes.linewidth": 0.8,
    "axes.labelsize": 8.8, "xtick.labelsize": 7.8, "ytick.labelsize": 7.8, "legend.fontsize": 7.8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#3a3f45",
    "figure.dpi": 600, "savefig.dpi": 600, "savefig.bbox": "tight", "savefig.pad_inches": 0.06, "pdf.fonttype": 42,
})
INK, G_DK, G_MD, NULLG = "#1a1a1a", "#555555", "#8a8a8a", "#9aa4af"
KSTYLE = {2: (INK, "o"), 16: (G_DK, "s"), 64: (G_MD, "^")}
BAND = 0.13

runs = defaultdict(lambda: {"oracle": [], "silK": []})
for line in open(os.path.join(RES, "pilot2s_scale.jsonl")):
    if line.strip():
        r = json.loads(line)
        k = (r["cond"], r["M"], r["K"], r["W"])
        runs[k]["oracle"].append(r["ari_oracle"]); runs[k]["silK"].append(r["ari_silK"])


def series(keys, method):
    """Mean and SD over seeds for each (cond, M, K, W) key that exists."""
    keys = [k for k in keys if k in runs]
    v = [np.array(runs[k][method]) for k in keys]
    return keys, np.array([x.mean() for x in v]), np.array([x.std() for x in v])


def draw(ax, x, m, sd, col, mk, ls, lw, filled=True, band=True, label=None):
    if band:
        ax.fill_between(x, np.clip(m - sd, -0.05, 1.0), np.clip(m + sd, -0.05, 1.0), color=col, alpha=BAND, lw=0, zorder=2)
    ax.plot(x, m, ls=ls, marker=mk, color=col, lw=lw, ms=3.2, zorder=3, label=label,
            markerfacecolor=col if filled else "white", markeredgecolor="white" if filled else col,
            markeredgewidth=0.5 if filled else 0.9)


def finish(ax, title):
    ax.axhline(0.0, ls=(0, (5, 3)), lw=0.8, color=NULLG, zorder=1)
    ax.set_ylim(-0.05, 1.05); ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_title(title, loc="left", fontsize=8.8)
    ax.tick_params(labelleft=True)


def style_legend(ax, handles):
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.31), frameon=False, ncol=1,
              handlelength=2.6, labelspacing=0.3)


fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(7.2, 2.75), sharey=True)
MS = [24 * 2 ** i for i in range(12)]

# (a) adding members at a fixed pool count
for K, (col, mk) in KSTYLE.items():
    for W, ls, lw in ((96, "-", 1.3), (24, (0, (4, 2)), 1.1)):
        keys, m, sd = series([("adverse", M, K, W) for M in MS], "oracle")
        draw(ax1, [k[1] for k in keys], m, sd, col, mk, ls, lw)
ax1.set_xscale("log", base=2)
ticks = [24, 384, 6144, 49152]
ax1.set_xticks(ticks); ax1.set_xticklabels([f"{t:,}" for t in ticks])
ax1.set_xticks(MS, minor=True); ax1.set_xticklabels([], minor=True)
ax1.set_xlabel("DERs in the aggregation  $M$")
ax1.set_ylabel("co-membership ARI")
finish(ax1, "(a) adding members")
style_legend(ax1, [Line2D([], [], color=G_DK, lw=1.3, ls="-", label="W = 96, true K"),
                   Line2D([], [], color=G_DK, lw=1.1, ls=(0, (4, 2)), label="W = 24, true K")])

# (b) adding pools at 768 DERs per pool
KS = [2, 4, 8, 16, 32, 64]
for W, method, col, mk, ls, lw, filled, lab in (
        (96, "oracle", INK, "o", "-", 1.3, True, "W = 96, true K"),
        (24, "oracle", G_DK, "s", (0, (4, 2)), 1.1, True, "W = 24, true K"),
        (24, "silK", G_MD, "s", (0, (1, 1.4)), 1.1, False, "W = 24, estimated K")):
    keys, m, sd = series([("adverse", 768 * K, K, W) for K in KS], method)
    draw(ax2, [k[2] for k in keys], m, sd, col, mk, ls, lw, filled=filled, label=lab)
ax2.set_xscale("log", base=2)
ax2.set_xticks(KS); ax2.set_xticklabels(KS); ax2.minorticks_off()
ax2.set_xlabel("pools  $K$  (768 DERs each)")
finish(ax2, "(b) adding pools")
style_legend(ax2, ax2.get_legend_handles_labels()[0])

# (c) estimating K at M = 12,288
WS = [6, 12, 24, 48, 96]
for K, (col, mk) in KSTYLE.items():
    keys, m, sd = series([("adverse", 12288, K, W) for W in WS], "oracle")
    draw(ax3, [k[3] for k in keys], m, sd, col, mk, "-", 1.3)
    keys, m, sd = series([("adverse", 12288, K, W) for W in WS], "silK")
    draw(ax3, [k[3] for k in keys], m, sd, col, mk, (0, (1, 1.4)), 1.1, filled=False, band=False)
ax3.set_xscale("log", base=2)
ax3.set_xticks(WS); ax3.set_xticklabels(WS); ax3.minorticks_off()
ax3.set_xlabel("observed windows  $W$")
finish(ax3, "(c) estimating K, 12,288 DERs")
style_legend(ax3, [Line2D([], [], color=G_DK, lw=1.3, ls="-", marker="o", ms=3.2, markeredgecolor="white", label="true K"),
                   Line2D([], [], color=G_DK, lw=1.1, ls=(0, (1, 1.4)), marker="o", ms=3.2, markerfacecolor="white",
                          markeredgecolor=G_DK, label="estimated K")])

# shared pool-count legend for (a) and (c)
fig.legend(handles=[Line2D([], [], color=c, marker=mk, lw=1.3, ms=3.6, markeredgecolor="white", label=f"K = {K}")
                    for K, (c, mk) in KSTYLE.items()],
           loc="lower center", bbox_to_anchor=(0.5, 0.915), ncol=3, frameon=False, handlelength=2.2,
           title="pool count in (a) and (c)", title_fontsize=7.8)
fig.tight_layout(w_pad=0.9, rect=(0, 0, 1, 0.92))   # leave room at the top for the shared legend
fig.savefig(OUT); fig.savefig(OUT[:-4] + ".pdf")   # PNG for the build, vector PDF for submission
plt.close(fig)
print("saved ->", OUT, "from", os.path.relpath(RES, HERE))
