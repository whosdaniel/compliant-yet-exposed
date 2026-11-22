# Pre-registration: E7 (unknown pool count) and E8 (scale), revision R1

**FROZEN 2026-10-27, before any ARI for E7/E8 was computed.** Authorized by the user ("let's go really big" + deadline 2026-11-24).
Only timing/memory benchmarks on random, structureless features (no pools, no ARI) were run beforehand; their numbers are recorded in `response_matrix.md` (E8).
Any analysis not listed here is reported as **exploratory** and labeled as such. Unfavorable results are reported as-is (memory `experimental-integrity-absolute`).

Responds to: R1.1 (attacker does not know K), R1.2 (hundreds/thousands of DERs), R4.2 (Ward complexity and scalability).

## Common machinery (identical to the published pipeline)
- Generators: `pilot2e_boundary.gen_joint` (cross-pool award correlation `corr`, within-pool synchronization `gamma`) and `pilot2_command_channel.gen(no_pools=True)` (negative control). Same channel constants, same features (z-normalized per-window count and size), same seeds.
- Ward tree: `linkage(pdist(feat, "euclidean"), "ward")`, computed once per realization.
- Metric: ARI from `pilot2i_metrics.ari`.

## Recovery methods
1. **oracle**: Ward cut at the true K (`fcluster(Z, K, "maxclust")`). This IS the published pipeline.
2. **silK**: Ward cut at K̂ = argmax silhouette (Euclidean) over the candidate set **{2, …, min(96, ⌊M/2⌋)}**. The candidate rule depends only on M, never on the true K. Ties go to the smallest K. Candidates whose cut is degenerate for silhouette are skipped; if all are skipped, K̂ = 2. For M > 6,144, silhouette is computed on one fixed uniform random subsample of 6,144 points (rng seed 10^6 + seed), the same subsample for every candidate K.
3. **hdbscan** (E7 only): `sklearn.cluster.HDBSCAN(min_cluster_size=5, copy=True)` on the same features, no K input. Noise points (label −1) are kept as one group for ARI. Not used in E8 (O(M²) memory at large M).

## Sanity check (pass/fail, run first)
The oracle method must reproduce the published values exactly (same seeds): `results/pilot2i_metrics.json` six operating points (headline 1.0, mild K2 0.7321, mild K5 0.5942, SOC-budget 0.1002, battery 0.0662, pessimistic 0.086) and `results/pilot2k_ari_curves.json` (c-sweep and gamma-sweep ARI means). Any mismatch halts the analysis until explained.

## E7: unknown K (50 seeds, 0..49)
- P1. The six published operating points, exactly as in `pilot2i_metrics.py`.
- P2. Published correlation sweep: corr ∈ {0, 0.5, 0.9, 0.99, 1.0}, gamma 1, W 24, K 2, M 24.
- P3. Published synchronization sweep: gamma ∈ {1, 0.75, 0.5, 0.25, 0}, corr 0, W 24, (K 2, M 24) and (K 5, M 30).
- P4. Pool-count sweep, favorable (corr 0, gamma 1, W 24): K ∈ {2, 3, 4, 5, 6, 8}, M = max(24, 6K).
- P5. Observation-budget sweep, favorable, K 5, M 30: W ∈ {4, 8, 16, 24, 48}.
- P6. Negative control (no pool structure, `gen(no_pools=True)`): K ∈ {2, 3, 5, 8}, M = max(24, 6K). Expect ARI ≈ 0 for every method; estimating K must not manufacture structure.
- Report per point: ARI mean ± SD for oracle, silK, hdbscan; K̂ exact-match rate, mean |K̂ − K|, mean K̂; HDBSCAN mean cluster count and noise fraction.

## E8: scale
- M ∈ {24·2^i, i = 0..11} = 24 … 49,152.
- K ∈ {2, 4, 8, 16, 32, 64}, only combinations with M ≥ 3K.
- W ∈ {6, 12, 24, 48, 96} for M ≤ 12,288; W ∈ {24, 96} for M ≥ 24,576.
- Conditions: favorable (corr 0, gamma 1); adverse (corr 0.5, gamma 0.6).
- Seeds: 20 (M ≤ 6,144), 10 (M = 12,288), 5 (M ≥ 24,576).
- Methods: oracle, silK.
- Record per run: ARI (both methods), K̂, wall-clock of pdist + Ward, wall-clock of K̂ selection, worker peak RSS. Results append to `results/pilot2s_scale.jsonl` (resumable).
- Report: ARI vs M per (K, W, condition); ARI over (K, W) at the largest M; runtime and memory vs M with an O(M²) fit.

## Interpretation guardrails (fixed in advance)
1. In this model, adding DERs to a pool can make clustering easier (same per-DER noise, more members). High ARI at large M is **not** evidence that real fleets of that size are vulnerable, and will not be written that way.
2. The informative scaling axes are the pool count K relative to the observation budget W, and the adverse conditions.
3. Real-world scale effects (NAT / CGNAT / cellular multiplexing, per-DER heterogeneity beyond gamma, vantage coverage) are outside the model and will be stated as such.
4. The scale ceiling (exact Ward on a 48 GB laptop ≈ 5×10^4 endpoints) is reported as a compute fact, not as a deployment claim.
