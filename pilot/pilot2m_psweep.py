"""pilot2m_psweep.py -- duty-cycle sensitivity (assumption A4). p=0.5 (per-window active prob) is the
max-entropy, most-distinguishing case; real duty cycles may be far from 0.5. Sweep p and report ARI
to show how recovery depends on award-state entropy. Reuses gen_joint (which has p_award) + analyze."""
from __future__ import annotations
import json, os
from pilot2i_metrics import analyze
from pilot2e_boundary import gen_joint

RES = os.path.join(os.path.dirname(__file__), "results")


def main():
    out = []
    for p in [0.05, 0.1, 0.25, 0.5, 0.75, 0.9]:
        for K, M in [(2, 24), (5, 30)]:
            r = analyze(lambda s, p=p, K=K, M=M: gen_joint(corr=0.0, gamma=1.0, W=24, K=K, M=M, p_award=p, seed=s),
                        K, f"p={p} K={K}")
            out.append({"p": p, "K": K, **r})
    json.dump(out, open(os.path.join(RES, "pilot2m_psweep.json"), "w"), indent=2)
    print(f"\nsaved -> {RES}/pilot2m_psweep.json")
    print("-> if ARI peaks near p=0.5 and falls at low/high p, duty cycle (A4) is a favorable condition.")


if __name__ == "__main__":
    main()
