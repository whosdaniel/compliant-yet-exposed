# Amendment 1: re-scoring the main results with the downlink record count alone (revision R1)

**FROZEN 2026-10-28, before any count-only result was computed except the diagnostic disclosed below.**
Decision by the author on 2026-10-28 (option B: re-run everything, even though it takes longer, because it is clearer).
This amends `prereg_E7_E8.md` and extends the same discipline to all main results of the paper. Unfavorable results are reported as-is.

## Why
The revision review (Codex finding F1, confirmed in `review_triage_pass1.md`) found that the manuscript describes the primary
observable as the per-window **downlink record count**, while the main generators cluster on `[z(count), z(size)]` with idle
records telemetry-sized (300 B). That feature vector is what a **bidirectional** observer sees. The manuscript's threat model
and mechanism make the downlink count the primary per-DER observable.

## Prior knowledge (disclosed)
One diagnostic was run before this amendment: `diagnostics/count_only_check.py` re-scored 25 operating points with the count
alone. Differences from count+size were at most 0.043 ARI, except at very short budgets (W = 2: 0.338 against 0.433; W = 4:
0.819 against 0.841). No other count-only result has been computed.

## What changes
Only the observer's feature vector: the z-normalized per-window record count (W dimensions) replaces `[count, size]`
(2W dimensions). Switch: environment variable `CYE_FEATURES=count`; outputs go to `pilot/results_countonly/`.
The default stays `count+size` until the regression check below passes.

## What stays fixed
Generators and their parameters, seeds, all grids (including the E7 and E8 grids of `prereg_E7_E8.md`), estimators (Ward cut
at the true K; silhouette rule with candidates 2 to min(96, M/2), ties to the smallest K, degenerate cuts skipped, fixed
6,144-point subsample with seed 10^6 + seed; HDBSCAN with minimum cluster size 5 and noise scored as one group), metrics (ARI,
optimal-assignment accuracy, pairwise F1, permutation null), and the interpretation guardrails of `prereg_E7_E8.md`.

## Scope
Re-run with the switch: `pilot2_command_channel.py`, `pilot2b_correlation.py`, `pilot2c_sensitivity.py`,
`pilot2d_within_pool.py`, `pilot2e_boundary.py`, `pilot2f_nuisance.py`, `pilot2h_disaggregation.py`, `pilot2n_drift.py`
(they build the features) and their dependents `pilot2i_metrics.py`, `pilot2j_wsweep.py`, `pilot2k_ari_curves.py`,
`pilot2m_psweep.py`, `pilot2o_fig_ari.py`, `pilot2r_unknown_k.py` (E7), `pilot2s_scale.py` (E8), `pilot2t_scale_analysis.py`.
Not re-run, because comparing count and size is their purpose: `pilot2g_mechanism.py`, `pilot2L_direction.py`,
`pilot2q_defense_factorial.py`. Not clustering: `pilot2p_hil.py`, `real_tls_measure.py`, `real_socket_capture.py`.

## Regression check (pass/fail, run first)
With `CYE_FEATURES=count+size` the modified code must reproduce the stored results exactly (every result field except
wall-clock timings and memory). For E8, a fixed random sample of stored runs is re-run as in `pilot2s_verify.py`.
Any mismatch halts the re-run until explained.

## Reporting
Count-only results become the primary numbers in the tables, figures, and text. The stored count+size results are reported
in a supplementary table as the bidirectional-observer variant, with the per-point difference. No grid, seed, or estimator
is changed after seeing count-only results. If a count-only result changes a conclusion, the text states it.
