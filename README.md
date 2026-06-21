# Compliant Yet Exposed: replication package

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20785008.svg)](https://doi.org/10.5281/zenodo.20785008)

This repository reproduces the experiments and data figures in the paper **"Compliant Yet Exposed: A Passive Multi-Tenant Membership Side-Channel in DER Aggregation"** (Woowi Kim, 2026).

Preprint: SSRN link to be added.
Preprint DOI: to be added once the SSRN version is posted (see "Citation" below).
Archived release: https://doi.org/10.5281/zenodo.20785008 (Zenodo; concept DOI, resolves to the latest version).

The paper studies a passive timing side-channel in distributed energy resource (DER) aggregation. A network observer that never decrypts traffic can recover dispatch-pool co-membership from the timing of per-DER control messages, under conditions stated in the paper. The study is a simulation grounded in real TLS message sizes measured over a local loopback connection. No real grid, DER, or third-party traffic is involved.

## What is in this repository

```
pilot/                     experiments and their saved outputs
  *.py                       the simulation model, clustering, metrics, and per-experiment drivers
  results/                   one JSON per experiment (the exact values the paper reports)
  results/real_socket_capture.pcap   the loopback TLS capture
figures/                   figure generators
  make_figures.py            the data figures (Figures 4, 5, 7, 8, 9, 10, 11)
  make_fig_defense_factorial.py   the defense factorial (Figure 6)
  figstyle.py                shared plot style
  figs/                      the rendered data figures (PNG)
requirements.txt           Python dependencies
Makefile                   shortcuts for the steps below
LICENSE, CITATION.cff      license and citation metadata
```

## Requirements

- Python 3.10 or newer (tested on 3.13).
- The Python packages in `requirements.txt` (NumPy, SciPy, Matplotlib, lxml).
- The `openssl` command line tool, needed only if you re-run the two loopback TLS scripts (`real_tls_measure.py`, `real_socket_capture.py`). They create a throwaway self-signed certificate in your temporary directory.

This package was tested on macOS and runs on Linux as well. On Windows, run the `python` commands shown below rather than `make` (which is not standard on Windows), and activate the virtual environment with `.venv\Scripts\activate` instead of `source .venv/bin/activate`. The two optional loopback TLS scripts need `openssl` available on the command line.

## Quick start: regenerate the figures from the saved results

This is the fast path. It uses the JSON files already in `pilot/results/` and runs in a few seconds.

```
python -m venv .venv && source .venv/bin/activate     # optional but recommended
pip install -r requirements.txt
make figures
```

Without `make`:

```
pip install -r requirements.txt
cd figures
python make_figures.py
python make_fig_defense_factorial.py
```

The figures are written to `figures/figs/`.

## Full reproduction: re-run every experiment

This re-runs all simulations from scratch, regenerates `pilot/results/`, and then the figures. Every script uses fixed random seeds, so a clean run reproduces the saved JSON values exactly. Results are reported as the mean and standard deviation over 50 seeds per condition. Expect a few minutes.

```
make all
```

Without `make`, run the scripts in `pilot/` (each writes its own JSON into `pilot/results/`), then run the figure step above. The order does not matter, because each experiment is self-contained.

## Which script produces which result

| Script | Produces | Used in |
| --- | --- | --- |
| `pilot/pilot2_command_channel.py` | core model, E1 to E6, attacker cost | Figure 7, baseline |
| `pilot/pilot2o_fig_ari.py` | co-membership vs controls, correlation sweep | Figures 5 and 8 |
| `pilot/pilot2q_defense_factorial.py` | defense by attacker-feature factorial | Figure 6 |
| `pilot/pilot2c_sensitivity.py` | background-contamination sweep | Figure 9 |
| `pilot/pilot2k_ari_curves.py` | within-pool synchronization sweep | Figure 10 |
| `pilot/pilot2n_drift.py` | patient observer under drift and churn | Figure 11 |
| `pilot/pilot2e_boundary.py` | recovery boundary | Table 1 |
| `pilot/pilot2j_wsweep.py` | observation-budget sweep at the stressed point | Section 8.3 |
| `pilot/pilot2i_metrics.py` | chance-adjusted re-analysis (ARI, permutation null) | Section 8 |
| `pilot/pilot2b,d,f,g,h,L,m_*.py` | correlation, within-pool, nuisance, mechanism, disaggregation, direction, and duty-cycle checks | Section 8 robustness checks |
| `pilot/real_tls_measure.py` | TLS-encrypted message sizes over loopback | Section 7 |
| `pilot/real_socket_capture.py` | idle vs active traffic shape over loopback, plus the `.pcap` | Section 7 |
| `pilot/pilot2p_hil.py` | per-DER command-emission loop (assumption A1) | Section 7 |

## What you can explore

Beyond reproducing the figures, you can change the model parameters in the scripts and re-run them to see how recovery responds:

- number of pools (K), observation budget (W), cross-pool award-timing correlation, and within-pool synchronization (gamma): `pilot/pilot2_command_channel.py` and `pilot/pilot2e_boundary.py`
- defenses and attacker features (count, size, or both): `pilot/pilot2q_defense_factorial.py`
- background-contamination level: `pilot/pilot2c_sensitivity.py`

Each script prints a summary and writes its JSON into `pilot/results/`, so you can compare runs and then regenerate the figures.

## Notes on scope

- The simulations are model-grade. Packet sizes come from real TLS encryption of schema-serialized protocol payloads on a local loopback connection. They are not captured from a deployed system.
- No real grid, DER, or third-party traffic is intercepted, and no confidential or access-controlled data is used. The loopback capture contains only synthetic payloads.
- Random seeds are fixed (50 seeds per condition), so a clean run is deterministic and reproduces the saved values.

## Citation

If you use this code or its results, please cite the paper. A `CITATION.cff` file is included for citation managers. The preprint DOI will be added here once the SSRN version is posted.

This software release is archived on Zenodo. To cite the code itself, use the concept DOI 10.5281/zenodo.20785008 (always resolves to the latest version). The DOI for this specific release (v1.0.0) is 10.5281/zenodo.20785009.

```
Woowi Kim. Compliant Yet Exposed: A Passive Multi-Tenant Membership Side-Channel
in DER Aggregation. 2026. Preprint: SSRN (DOI to be added).
```

## License

Released under the MIT License. See `LICENSE`.
