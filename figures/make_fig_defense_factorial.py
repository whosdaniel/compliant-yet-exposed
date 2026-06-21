"""make_fig_defense_factorial.py — Fig 6: defense x attacker-feature factorial (achromatic).
Reads pilot2q_defense_factorial.json (NOT hardcoded). Two STACKED panels (full width each, readable):
  top    = downlink command channel (primary): constant cadence alone closes it.
  bottom = bidirectional envelope: count and size each leak, so both are required.
Each panel: x = defense {none, padding-only, cadence-only, both}; 3 bars = count-only / size-only /
joint attacker ARI (favorable corner K=2, W=24). Null band shaded. Verdicts go in the panel titles
+ caption (kept off the bars to avoid overlap).
Run:  python make_fig_defense_factorial.py
"""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from figstyle import apply, ACC, TEAL, RED, MUT, INK
apply()

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "pilot", "results", "pilot2q_defense_factorial.json")
OUT = os.path.join(HERE, "figs", "fig_defense_factorial.png")

d = json.load(open(DATA))
CORNER = "favorable (K=2, W=24)"
DEFS = ["none", "padding", "cadence", "both"]
DEF_LABEL = {"none": "no\ndefense", "padding": "padding\nonly", "cadence": "cadence\nonly", "both": "cadence\n+ padding"}
# achromatic shade ramp + hatch on joint for extra separation in grayscale
FEATS = [("count_only", "count attacker", ACC, ""),
         ("size_only", "size attacker", TEAL, ""),
         ("joint", "count + size attacker", RED, "/////")]


def val(model, dfn, feat):
    v = d["cells"][f"{model}|{CORNER}|{dfn}"][feat]["ari"]
    return max(0.0, v)  # clamp tiny negatives to 0 for display


def null_band(model):
    qs = [d["cells"][f"{model}|{CORNER}|{dfn}"][f]["null975"] for dfn in DEFS for f, *_ in FEATS]
    return float(np.mean(qs))


fig, axes = plt.subplots(2, 1, figsize=(7.2, 6.8), sharex=True)
titles = {"downlink": "(a) Downlink command channel (primary) — cadence alone closes it",
          "bidir": "(b) Bidirectional envelope — cadence-only leaves the size channel"}
x = np.arange(len(DEFS)); w = 0.26
for ax, model in zip(axes, ["downlink", "bidir"]):
    nb = null_band(model)
    ax.axhspan(0, nb, color=MUT, alpha=0.22, lw=0, zorder=0)
    ax.text(3.40, nb / 2 + 0.015, "null", color="#5a6470", fontsize=10, va="center", ha="right", style="italic")
    for j, (fk, flab, col, hatch) in enumerate(FEATS):
        vals = [val(model, dfn, fk) for dfn in DEFS]
        bars = ax.bar(x + (j - 1) * w, vals, w, color=col, label=flab, edgecolor=INK,
                      linewidth=0.7, hatch=hatch, zorder=3)
        for b, v in zip(bars, vals):
            # label EVERY bar so a closed channel reads as a measured "0.00", not a missing/buggy gap
            yy = v + 0.02 if v >= 0.12 else nb + 0.03
            ax.text(b.get_x() + b.get_width() / 2, yy, f"{v:.2f}", ha="center", va="bottom",
                    fontsize=8, color=INK)
    ax.set_title(titles[model], fontsize=11, pad=6, loc="left")
    ax.set_ylim(0, 1.2); ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_ylabel("co-membership ARI")
axes[1].set_xticks(x); axes[1].set_xticklabels([DEF_LABEL[dn] for dn in DEFS])
axes[0].legend(loc="upper right", ncol=1, fontsize=10, handlelength=1.6, borderaxespad=0.5)
fig.tight_layout(h_pad=1.6)
fig.savefig(OUT)
print("wrote", OUT)
