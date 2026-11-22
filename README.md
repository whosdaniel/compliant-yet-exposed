# Compliant Yet Exposed: replication package

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20785008.svg)](https://doi.org/10.5281/zenodo.20785008)

This repository reproduces the experiments, figures, and tables in the paper **"Compliant Yet Exposed: A Passive Multi-Tenant Membership Side-Channel in DER Aggregation"** (Woowi Kim, 2026). Version 1.1 accompanies the revised manuscript.

Preprint: https://ssrn.com/abstract=6973838
Preprint DOI: 10.2139/ssrn.6973838
Archived release: https://doi.org/10.5281/zenodo.20785008 (Zenodo; concept DOI, resolves to the latest version).

The paper studies a passive timing side-channel in distributed energy resource (DER) aggregation. A network observer that never decrypts traffic can recover dispatch-pool co-membership from the timing of per-DER control messages, under conditions stated in the paper. The study is a simulation grounded in real TLS message sizes measured over a local loopback connection. No real grid, DER, or third-party traffic is involved.

## What changed in version 1.1

- **Two observers.** The paper's results now use the downlink observer, whose feature for each DER is the per-window record count. They are in `pilot/results_countonly/`. Version 1.0 reported a bidirectional observer that also sees each window's mean record size, while the paper described the downlink observer; those results stay in `pilot/results/` as the bidirectional variant, and the paper's Supplementary Table S1 lists both. Every clustering script takes the observer from the environment variable `CYE_FEATURES` (`count+size`, the default, or `count`) and its output folder from `CYE_RESULTS`.
- **New experiments.** E7 recovers membership without knowing the number of pools (`pilot2r_unknown_k.py`). E8 grows the fleet from 24 to 49,152 DERs (`pilot2s_scale.py`, analysis `pilot2t_scale_analysis.py`, integrity check `pilot2s_verify.py`).
- **Six stored decimals.** The result files used to round means and SDs to two to four decimals, so some values in the paper were rounded twice. They were regenerated with six decimals and checked against the earlier rounding (`precision_regen.py`; reports in `revision/`).
- **Background sweep check.** `pilot2c_sensitivity.py` with `CYE_BG_NORM=der` standardizes each DER across windows (the post hoc check in Fig. 11) and writes `pilot2c_sensitivity_perder.json`.
- **Revision records.** `revision/` holds the design files fixed before the new runs, with their SHA-256 hashes, the regression and precision reports, and the diagnostics cited in the paper and its supplementary material.
- **One-command check.** `pilot/verify_results.py` re-runs every fast experiment for both observers and compares each result field with the stored files.

## What is in this repository

```
pilot/                       experiments and their saved outputs
  *.py                         the simulation model, clustering, metrics, and per-experiment drivers
  results_countonly/           downlink observer: the values the paper reports (plus run_manifest.json and logs/)
  results/                     bidirectional variant, and the files that do not depend on the observer
                               (TLS measurements, loopback capture real_socket_capture.pcap, direction ablation,
                               defense factorial, command-emission loop)
  verify_results.py            re-run and compare every fast result file, both observers
figures/                     figure generators and the rendered data figures (figs/)
revision/                    design files, hashes, reports, and diagnostics of the revision
supplementary/               the E8 configuration file of the paper's supplementary material (CSV)
requirements.txt, Makefile   dependencies and shortcuts
LICENSE, CITATION.cff        license and citation metadata
```

## Requirements

- Python 3.10 or newer (tested on Python 3.13.12 with NumPy 2.4.6, SciPy 1.17.1, scikit-learn 1.9.0, Matplotlib 3.11.0).
- The packages in `requirements.txt` (NumPy, SciPy, scikit-learn, Matplotlib, lxml).
- The `openssl` command line tool, needed only to re-run the loopback TLS scripts (`real_tls_measure.py`, `real_socket_capture.py`), which create a throwaway self-signed certificate in your temporary directory.
- E8 at full size: about 22 GB of memory for one run at 49,152 DERs, and about 2 to 3 hours on an 18-core laptop for the whole grid. `pilot2s_scale.py` sizes its worker pool to a 34 GB memory budget (`MEM_BUDGET_GB`); lower it on a smaller machine. The worker count changes only the run time, not the results.

The package was tested on macOS and runs on Linux as well. On Windows, run the `python` commands below rather than `make`, set environment variables with `set NAME=value` before a command, and activate the virtual environment with `.venv\Scripts\activate`.

## Quick start: regenerate the figures from the saved results

```
python -m venv .venv && source .venv/bin/activate     # optional but recommended
pip install -r requirements.txt
make figures
```

Without `make`: `cd figures`, then run `python make_figures.py`, `python make_fig_scale.py`, and `python make_fig_defense_factorial.py`. The figures (PNG and vector PDF) are written to `figures/figs/` and read `pilot/results_countonly/` by default.

## Check the stored results

```
make check       # about one minute
make check-e8    # a few minutes
```

`make check` (`cd pilot && python verify_results.py ../.check`) re-runs every fast experiment for both observers into the scratch folder `.check/` and compares each result field with the stored files, exactly; only wall-clock and memory fields are exempt. It never writes into the stored result folders. `make check-e8` re-runs a fixed random sample of twelve stored E8 runs for each observer and compares them exactly (`pilot2s_verify.py`). Every script uses fixed random seeds, so these comparisons are deterministic.

## Full reproduction

These targets recompute the stored result files in place.

```
make experiments            # fast experiments, both observers (minutes)
make e8                     # E8 for the downlink observer (hours)
make e8-bidirectional       # E8 for the bidirectional variant (hours)
make measurements           # TLS sizes, loopback capture, command-emission loop
```

Without `make`, run a script from `pilot/`; for the paper's observer, set the variables first, for example `CYE_FEATURES=count CYE_RESULTS=results_countonly python pilot2k_ari_curves.py`. E8 appends one line per run to `pilot2s_scale.jsonl` and skips runs already recorded there; to recompute it from scratch, point `CYE_RESULTS` at an empty folder. `make measurements` replaces the stored capture and measurements with a new loopback run, whose timestamps and certificate differ.

## Which script produces which result

Section, figure, and table numbers refer to the revised paper.

| Script | Produces | Used in |
| --- | --- | --- |
| `pilot2_command_channel.py` | core model; co-membership versus function (E2) and no-structure control (E6); attacker cost (E4); multi-pool separation (E5); cheap defenses | Fig. 8; Sections 6.1, 6.3, 7.1 |
| `pilot2o_fig_ari.py` | co-membership ARI of real recovery and the controls; correlation sweep at three observation budgets | Table 2, Figs. 5 and 6 |
| `pilot2k_ari_curves.py` | correlation and within-pool synchronization sweeps (accuracy and ARI) | Tables 3 and 4, Fig. 7 |
| `pilot2e_boundary.py` | recovery boundary and no-structure floors | Table 4, Section 6.3 |
| `pilot2i_metrics.py` | chance-corrected metrics, permutation null, joint operating points | Table 5 |
| `pilot2j_wsweep.py` | observation budget at the stressed point | Section 6.3 |
| `pilot2n_drift.py` | patient observer under drift and membership churn | Fig. 9 |
| `pilot2r_unknown_k.py` | E7, recovery without the pool count | Table 6, Supplementary Table S2 |
| `pilot2s_scale.py`, `pilot2t_scale_analysis.py`, `pilot2s_verify.py` | E8, fleets of 24 to 49,152 DERs; clustering cost | Fig. 10, Section 6.4, Supplementary Tables S3 and S4 |
| `pilot2c_sensitivity.py` | background contamination, both standardizations | Fig. 11 |
| `pilot2q_defense_factorial.py` | defense by attacker-feature factorial | Fig. 12 |
| `pilot2b_correlation.py`, `pilot2d_within_pool.py` | correlation and within-pool sweeps (accuracy) | Supplementary Table S1 |
| `pilot2f_nuisance.py`, `pilot2g_mechanism.py`, `pilot2h_disaggregation.py`, `pilot2L_direction.py`, `pilot2m_psweep.py` | per-DER variation, temporal-shuffle control and feature ablation, disaggregation, traffic direction, duty cycle | Sections 6.1, 6.2, 6.5 |
| `real_tls_measure.py`, `real_socket_capture.py` | TLS record sizes; loopback capture and `.pcap` | Fig. 4, Section 5.3 |
| `pilot2p_hil.py` | per-DER command-emission loop (assumption A1) | Section 5.3 |
| `amendment1_regression.py`, `amendment1_countonly.py`, `precision_regen.py` | regression check, downlink re-run, and six-decimal regeneration of the revision | `revision/` |

## The revision folder

- `prereg_E7_E8.md`, `prereg_amendment1_count_only.md`, `prereg_amendment1a_scope.md`: the E7 and E8 design and the two amendments that moved the paper's results to the downlink observer, each written and frozen before the runs it governs. They are working records written with AI assistance, as declared in the paper, and were not deposited in an external registry. They are published unchanged; `SHA256SUMS` lists their hashes (`cd revision && shasum -a 256 -c SHA256SUMS`).
- `amendment1_regression_report.json`: before the downlink re-run, the modified scripts reproduced every stored result field with the original features.
- `precision_regen_report.json`, `precision_regen_pilot2L_report.json`: the six-decimal regeneration, with every new value inside the rounding interval of the stored one. The direction ablation shares the ARI routine whose rounding changed and was regenerated the same way.
- `diagnostics/`: post hoc checks cited in the paper and its supplementary material (per-seed details of E7, every E8 number in the text, a full-precision re-run of one E8 configuration, the TLS records read off the loopback capture, and the count-only diagnostic disclosed in amendment 1), each with its output.

The stored records name these files by their path in the development tree (`reference/revision_r1/`); in this package they are in `revision/`. Local absolute path prefixes in the run logs and in one report were replaced by `<repo>` or `<scratch>`; nothing else in them was changed.

## Notes on scope

- The simulations are model-grade. Packet sizes come from real TLS encryption of schema-serialized protocol payloads on a local loopback connection. They are not captured from a deployed system.
- No real grid, DER, or third-party traffic is intercepted, and no confidential or access-controlled data is used. The loopback capture contains only synthetic payloads.
- Random seeds are fixed (50 seeds per condition unless stated), so a clean run is deterministic and reproduces the saved values.

## Citation

If you use this code or its results, please cite the paper. A `CITATION.cff` file is included for citation managers. Preprint: SSRN (DOI 10.2139/ssrn.6973838).

This software release is archived on Zenodo. To cite the code itself, use the concept DOI 10.5281/zenodo.20785008, which always resolves to the latest version; the Zenodo record lists the DOI of each version.

```
Woowi Kim. Compliant Yet Exposed: A Passive Multi-Tenant Membership Side-Channel
in DER Aggregation. 2026. Preprint, SSRN. DOI 10.2139/ssrn.6973838.
```

## License

Released under the MIT License. See `LICENSE`.
