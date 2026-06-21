"""make_diagrams_svg.py — the three concept diagrams (Fig 1 threat model, Fig 2 three-layer
compartmentalization, Fig 3 command-down mechanism) as hand-authored SVG, rendered to high-DPI
PNG via headless Chrome. Layouts tuned for legibility (generous boxes, no cramped labels).
Achromatic / journal palette: infrastructure in light grays, the adversary in a dark fill with
white text (so it stands out without hue), the two pools by shade + complementary fill pattern.
Vector -> crisp PNG.
"""
import os, subprocess, tempfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
FIGS = os.path.join(HERE, "figs")


def _find_chrome():
    """Locate a Chrome or Chromium binary. Override by setting the CHROME environment variable.
    Only needed to regenerate the diagram PNGs; the rendered PNGs are included in figs/."""
    env = os.environ.get("CHROME")
    if env and os.path.exists(env):
        return env
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        shutil.which("google-chrome"), shutil.which("google-chrome-stable"),
        shutil.which("chromium"), shutil.which("chromium-browser"), shutil.which("chrome"),
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


CHROME = _find_chrome()

# ---- achromatic palette (no hue) ----
ACC, ACC_F, ACC_D = "#666666", "#eef0f1", "#2b2b2b"          # infrastructure: med border / light fill / dark text
RED, RED_F, RED_D = "#1a1a1a", "#3a3f45", "#ffffff"          # adversary: dark stroke+arrows / dark fill / WHITE text
TEAL, TEAL_F, TEAL_D = "#444444", "#e3e5e7", "#2b2b2b"       # pool A: dark squares
GOLD, GOLD_F, GOLD_D, GOLD_C = "#8a8a8a", "#f2f3f4", "#3a3a3a", "#9c9c9c"  # pool B: mid squares
GRY, GRY_F, GRY_S = "#8a8a8a", "#f1f2f3", "#9aa4af"          # neutral medium / grid operator
INK, MUT = "#1a1a1a", "#5f6b78"

FONT = "Georgia, 'Times New Roman', serif"

# ----------------------------------------------------------------------------- Fig 1: threat model
THREAT = f"""<svg viewBox="0 0 680 322" xmlns="http://www.w3.org/2000/svg" font-family="{FONT}">
  <rect x="0" y="0" width="680" height="322" fill="#ffffff"/>
  <defs>
    <marker id="ar" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{GRY}"/></marker>
    <marker id="arR" markerWidth="8" markerHeight="8" refX="6.5" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="{RED}"/></marker>
  </defs>

  <rect x="24" y="16" width="12" height="12" rx="2" fill="{RED_F}" stroke="{RED}" stroke-width="1.5"/>
  <text x="42" y="26" font-size="12" fill="{INK}">= adversary vantage point  (passive: reads timing + size only, no decryption)</text>

  <!-- control-network boundary (top raised so the label clears the boxes below it) -->
  <rect x="22" y="48" width="340" height="192" rx="12" fill="none" stroke="{ACC}" stroke-width="1.6" stroke-dasharray="7 5"/>
  <text x="36" y="68" font-size="12.5" font-weight="bold" fill="{ACC_D}">aggregation / control network</text>

  <!-- aggregator -->
  <rect x="44" y="86" width="120" height="64" rx="9" fill="{ACC_F}" stroke="{ACC}" stroke-width="2"/>
  <text x="104" y="114" font-size="15" font-weight="bold" fill="{ACC_D}" text-anchor="middle">Aggregator</text>
  <text x="104" y="133" font-size="11" fill="{MUT}" text-anchor="middle">disaggregates AGC</text>

  <!-- data flow: aggregator -> ISP (the foothold TAPS this; it is not inline) -->
  <text x="268" y="106" font-size="10.5" fill="{MUT}" text-anchor="middle">per-DER encrypted commands</text>
  <path d="M164,118 L369,118" stroke="{GRY}" stroke-width="2" fill="none" marker-end="url(#ar)"/>

  <!-- ISP / public internet (medium) -->
  <rect x="372" y="86" width="112" height="64" rx="10" fill="{GRY_F}" stroke="{GRY_S}" stroke-width="1.8"/>
  <text x="428" y="112" font-size="12.5" font-weight="bold" fill="{INK}" text-anchor="middle">ISP /</text>
  <text x="428" y="130" font-size="12.5" font-weight="bold" fill="{INK}" text-anchor="middle">public internet</text>

  <!-- DER stack -->
  <g fill="{TEAL_F}" stroke="{TEAL}" stroke-width="2">
    <rect x="524" y="40" width="132" height="44" rx="9"/>
    <rect x="524" y="96" width="132" height="44" rx="9"/>
    <rect x="524" y="152" width="132" height="44" rx="9"/>
  </g>
  <g font-size="14.5" font-weight="bold" fill="{TEAL_D}" text-anchor="middle">
    <text x="590" y="67">DER</text>
    <text x="590" y="123">DER</text>
    <text x="590" y="179">DER</text>
  </g>

  <!-- ISP -> DER -->
  <g stroke="{GRY}" stroke-width="2" fill="none" marker-end="url(#ar)">
    <path d="M484,108 L521,64"/>
    <path d="M484,118 L521,118"/>
    <path d="M484,128 L521,172"/>
  </g>

  <!-- adversary vantage 1: foothold (PRIMARY) -- taps the egress flow -->
  <rect x="210" y="178" width="140" height="54" rx="9" fill="{RED_F}" stroke="{RED}" stroke-width="2"/>
  <text x="280" y="202" font-size="13.5" font-weight="bold" fill="{RED_D}" text-anchor="middle">Passive foothold</text>
  <text x="280" y="219" font-size="10.5" fill="{RED_D}" text-anchor="middle">PRIMARY vantage</text>
  <path d="M280,176 L280,121" stroke="{RED}" stroke-width="1.6" stroke-dasharray="5 4" fill="none" marker-end="url(#arR)"/>

  <!-- adversary vantage 2: on-path / ISP (SECONDARY) -- taps the ISP medium -->
  <rect x="372" y="214" width="112" height="52" rx="9" fill="{RED_F}" stroke="{RED}" stroke-width="2"/>
  <text x="428" y="235" font-size="12.5" font-weight="bold" fill="{RED_D}" text-anchor="middle">on-path / ISP</text>
  <text x="428" y="251" font-size="10.5" fill="{RED_D}" text-anchor="middle">SECONDARY (weaker)</text>
  <path d="M428,212 L428,152" stroke="{RED}" stroke-width="1.6" stroke-dasharray="5 4" fill="none" marker-end="url(#arR)"/>

  <line x1="22" y1="286" x2="658" y2="286" stroke="#e2e8ef" stroke-width="1"/>
  <text x="340" y="304" font-size="11" font-style="italic" fill="{MUT}" text-anchor="middle">Out of scope:  break encryption  ·  seize control plane  ·  read membership roster  ·  downstream manipulation</text>
</svg>"""

# --------------------------------------------------------------- Fig 2: three-layer compartmentalization
THREE_LAYER = f"""<svg viewBox="0 0 680 268" xmlns="http://www.w3.org/2000/svg" font-family="{FONT}">
  <rect x="0" y="0" width="680" height="268" fill="#ffffff"/>
  <defs>
    <marker id="arR2" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{RED}"/></marker>
  </defs>

  <text x="24" y="24" font-size="11.5" fill="{MUT}">Three distinct layers each keep dispatch-pool membership non-public:</text>

  <!-- three layers -->
  <g>
    <rect x="24" y="38" width="192" height="64" rx="9" fill="{ACC_F}" stroke="{ACC}" stroke-width="2"/>
    <text x="120" y="66" font-size="14" font-weight="bold" fill="{ACC_D}" text-anchor="middle">Market</text>
    <text x="120" y="86" font-size="10.5" fill="{MUT}" text-anchor="middle">single aggregate resource</text>

    <rect x="244" y="38" width="192" height="64" rx="9" fill="{ACC_F}" stroke="{ACC}" stroke-width="2"/>
    <text x="340" y="66" font-size="13.5" font-weight="bold" fill="{ACC_D}" text-anchor="middle">Regulatory / data</text>
    <text x="340" y="86" font-size="10.5" fill="{MUT}" text-anchor="middle">access-controlled</text>

    <rect x="464" y="38" width="192" height="64" rx="9" fill="{ACC_F}" stroke="{ACC}" stroke-width="2"/>
    <text x="560" y="66" font-size="13.5" font-weight="bold" fill="{ACC_D}" text-anchor="middle">Protocol (2030.5)</text>
    <text x="560" y="86" font-size="10.5" fill="{MUT}" text-anchor="middle">endpoint-scoped</text>
  </g>

  <!-- the three layers compartmentalize (guard) the secret -->
  <g stroke="{GRY_S}" stroke-width="1.4" fill="none" stroke-dasharray="4 3">
    <path d="M120,102 L312,174"/>
    <path d="M340,102 L340,174"/>
    <path d="M560,102 L368,174"/>
  </g>
  <rect x="286" y="127" width="108" height="18" fill="#ffffff"/>
  <text x="340" y="140" font-size="11" fill="{MUT}" text-anchor="middle">compartmentalize</text>

  <!-- protected secret -->
  <rect x="240" y="176" width="200" height="66" rx="9" fill="#e8eaed" stroke="{INK}" stroke-width="2"/>
  <rect x="332" y="186" width="16" height="11" rx="2" fill="{INK}"/>
  <path d="M335,186 v-3 a5,5 0 0,1 10,0 v3" fill="none" stroke="{INK}" stroke-width="2"/>
  <text x="340" y="216" font-size="12.5" font-weight="bold" fill="{INK}" text-anchor="middle">dispatch-pool co-membership</text>
  <text x="340" y="232" font-size="10" font-style="italic" fill="{MUT}" text-anchor="middle">the protected property</text>

  <!-- passive timing side-channel: recovers it OUTSIDE all three (2-line title so it is not cramped) -->
  <rect x="472" y="176" width="184" height="66" rx="9" fill="{RED_F}" stroke="{RED}" stroke-width="2"/>
  <text x="564" y="199" font-size="12.5" font-weight="bold" fill="{RED_D}" text-anchor="middle">Passive timing</text>
  <text x="564" y="216" font-size="12.5" font-weight="bold" fill="{RED_D}" text-anchor="middle">side-channel</text>
  <text x="564" y="232" font-size="9.5" fill="{RED_D}" text-anchor="middle">inference path outside all three</text>
  <path d="M470,209 L443,209" stroke="{RED}" stroke-width="2" fill="none" marker-end="url(#arR2)"/>
</svg>"""

# ------------------------------------------------------------------- Fig 3: command-down mechanism
MECHANISM = f"""<svg viewBox="0 0 680 292" xmlns="http://www.w3.org/2000/svg" font-family="{FONT}">
  <rect x="0" y="0" width="680" height="292" fill="#ffffff"/>
  <defs>
    <marker id="g3" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{GRY}"/></marker>
    <marker id="g3r" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{RED}"/></marker>
  </defs>

  <text x="24" y="22" font-size="10.5" fill="{MUT}">Market awards gate each pool's active windows; the 4 s cadence makes that per-DER activity observable.</text>

  <!-- grid operator -->
  <rect x="10" y="126" width="82" height="50" rx="9" fill="{GRY_F}" stroke="{GRY_S}" stroke-width="1.8"/>
  <text x="51" y="155" font-size="10.5" font-weight="bold" fill="{INK}" text-anchor="middle">Grid operator</text>

  <!-- "4 s AGC" lifted clear of the arrow below it -->
  <text x="111" y="135" font-size="9.5" fill="{MUT}" text-anchor="middle">4 s AGC</text>
  <path d="M92,151 L130,151" stroke="{GRY}" stroke-width="2" fill="none" marker-end="url(#g3)"/>

  <!-- aggregator -->
  <rect x="132" y="122" width="92" height="58" rx="9" fill="{ACC_F}" stroke="{ACC}" stroke-width="2"/>
  <text x="178" y="147" font-size="13" font-weight="bold" fill="{ACC_D}" text-anchor="middle">Aggregator</text>
  <text x="178" y="164" font-size="9.5" fill="{MUT}" text-anchor="middle">disaggregates</text>

  <!-- short trunk, two-line label, then long branch arrows -->
  <text x="254" y="131" font-size="9.5" fill="{MUT}" text-anchor="middle">per-DER</text>
  <text x="254" y="143" font-size="9.5" fill="{MUT}" text-anchor="middle">commands</text>
  <path d="M224,151 L284,151" stroke="{GRY}" stroke-width="2" fill="none"/>
  <circle cx="284" cy="151" r="2.6" fill="{GRY}"/>
  <g stroke="{GRY}" stroke-width="2" fill="none" marker-end="url(#g3)">
    <path d="M284,151 L342,87"/>
    <path d="M284,151 L342,215"/>
  </g>

  <!-- Pool A (dark squares) -->
  <rect x="344" y="46" width="140" height="72" rx="9" fill="{TEAL_F}" stroke="{TEAL}" stroke-width="2"/>
  <text x="372" y="88" font-size="14" font-weight="bold" fill="{TEAL_D}" text-anchor="middle">Pool A</text>
  <g stroke="{TEAL}" stroke-width="1.4">
    <rect x="398" y="64" width="16" height="16" rx="2" fill="{TEAL}"/>
    <rect x="419" y="64" width="16" height="16" rx="2" fill="#ffffff"/>
    <rect x="440" y="64" width="16" height="16" rx="2" fill="{TEAL}"/>
    <rect x="461" y="64" width="16" height="16" rx="2" fill="#ffffff"/>
  </g>
  <text x="414" y="106" font-size="9" fill="{TEAL_D}" text-anchor="middle">co-members share this pattern</text>

  <!-- Pool B (mid squares, complementary pattern) -->
  <rect x="344" y="184" width="140" height="72" rx="9" fill="{GOLD_F}" stroke="{GOLD}" stroke-width="2"/>
  <text x="372" y="226" font-size="14" font-weight="bold" fill="{GOLD_D}" text-anchor="middle">Pool B</text>
  <g stroke="{GOLD}" stroke-width="1.4">
    <rect x="398" y="202" width="16" height="16" rx="2" fill="#ffffff"/>
    <rect x="419" y="202" width="16" height="16" rx="2" fill="{GOLD_C}"/>
    <rect x="440" y="202" width="16" height="16" rx="2" fill="#ffffff"/>
    <rect x="461" y="202" width="16" height="16" rx="2" fill="{GOLD_C}"/>
  </g>
  <text x="414" y="244" font-size="9" fill="{GOLD_D}" text-anchor="middle">co-members share this pattern</text>

  <!-- passive observer (centered on the row, y=151) -->
  <rect x="560" y="115" width="104" height="72" rx="9" fill="{RED_F}" stroke="{RED}" stroke-width="2"/>
  <text x="612" y="137" font-size="11.5" font-weight="bold" fill="{RED_D}" text-anchor="middle">Passive observer</text>
  <text x="612" y="154" font-size="9.5" fill="{RED_D}" text-anchor="middle">clusters by</text>
  <text x="612" y="167" font-size="9.5" fill="{RED_D}" text-anchor="middle">shared timing</text>

  <!-- long mirrored arrows: pool centres (82 / 220) -> observer (151 +/- 13) -->
  <g stroke="{RED}" stroke-width="1.8" fill="none" stroke-dasharray="6 4" marker-end="url(#g3r)">
    <path d="M486,82 L558,138"/>
    <path d="M486,220 L558,164"/>
  </g>
  <text x="612" y="207" font-size="10" font-weight="bold" fill="{RED}" text-anchor="middle">recovers the pools</text>

  <!-- legend + footnote -->
  <rect x="24" y="264" width="11" height="11" rx="2" fill="{TEAL_F}" stroke="{TEAL}" stroke-width="1.4"/>
  <text x="40" y="273" font-size="10" fill="{INK}">Pool A</text>
  <rect x="92" y="264" width="11" height="11" rx="2" fill="{GOLD_F}" stroke="{GOLD}" stroke-width="1.4"/>
  <text x="108" y="273" font-size="10" fill="{INK}">Pool B</text>
  <text x="656" y="273" font-size="10.5" font-style="italic" fill="{MUT}" text-anchor="end">Survives encryption — the leak is in timing, not content.</text>
</svg>"""

DIAGRAMS = {
    "diag_threat_model": (THREAT, 680, 322),
    "diag_three_layer": (THREE_LAYER, 680, 268),
    "diag_mechanism": (MECHANISM, 680, 292),
}


def render(name, svg, w, h, scale=4):
    out = os.path.join(FIGS, name + ".png")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, dir="/tmp") as f:
        f.write(f"<!doctype html><html><head><meta charset='utf-8'>"
                f"<style>*{{margin:0;padding:0}}html,body{{width:{w}px;height:{h}px}}</style></head>"
                f"<body>{svg}</body></html>")
        html = f.name
    if os.path.exists(out):
        os.remove(out)
    try:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        f"--screenshot={out}", f"--window-size={w},{h}",
                        f"--force-device-scale-factor={scale}", "file://" + html],
                       timeout=90, capture_output=True)
    except subprocess.TimeoutExpired:
        print("WARN: chrome timeout for", name)
    finally:
        os.remove(html)
    sz = os.path.getsize(out) if os.path.exists(out) else 0
    print(f"  {name}.png  {w*scale}x{h*scale}px  {sz:,} bytes" if sz else f"  {name}: FAILED")


if __name__ == "__main__":
    if CHROME is None:
        raise SystemExit(
            "Chrome or Chromium was not found. Set the CHROME environment variable to your "
            "browser binary, or install Chrome/Chromium. This step only regenerates the three "
            "concept diagrams; the rendered PNGs are already included in figs/.")
    print("rendering SVG diagrams ->", FIGS)
    for name, (svg, w, h) in DIAGRAMS.items():
        render(name, svg, w, h)
