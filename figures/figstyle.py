"""figstyle.py — shared clean-minimal design system for the data figures (matches the SVG diagrams
and the paper's Times body font). Import and call apply() at the top of a figure script."""
import matplotlib as mpl

# achromatic / journal palette (no hue). Ordered shade ramp for grouped bars:
#   ACC = darkest (primary / count), TEAL = mid (size), RED = light (joint).
ACC, ACC2, TEAL, RED, MUT, INK = "#2b2b2b", "#565656", "#787878", "#b4b4b4", "#a6a6a6", "#1a1a1a"
GRID = "#e6e6e6"


def apply():
    mpl.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Georgia", "DejaVu Serif"],
        "font.size": 12.5, "axes.titlesize": 13, "axes.labelsize": 12.5,
        "axes.linewidth": 0.9, "axes.edgecolor": "#3a3f45", "axes.labelcolor": INK,
        "axes.labelpad": 6.0,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": False, "axes.axisbelow": True,
        "grid.color": GRID, "grid.linewidth": 0.9,
        "xtick.color": INK, "ytick.color": INK,
        "xtick.labelsize": 11, "ytick.labelsize": 11,
        "xtick.major.size": 4, "ytick.major.size": 4, "xtick.major.width": 0.8, "ytick.major.width": 0.8,
        "legend.frameon": False, "legend.fontsize": 10.5, "legend.handlelength": 1.8,
        "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.12,
        "lines.linewidth": 2.0, "lines.markersize": 6, "lines.markeredgewidth": 0.9,
        "lines.markeredgecolor": "white",
    })
