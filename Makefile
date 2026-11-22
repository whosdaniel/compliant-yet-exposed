PY ?= python

# Fast experiments that cluster on the observer's features (both observers).
FAST = pilot2_command_channel pilot2b_correlation pilot2c_sensitivity pilot2d_within_pool pilot2e_boundary \
       pilot2f_nuisance pilot2g_mechanism pilot2h_disaggregation pilot2i_metrics pilot2j_wsweep pilot2k_ari_curves \
       pilot2m_psweep pilot2n_drift pilot2o_fig_ari pilot2r_unknown_k
DOWN = CYE_FEATURES=count CYE_RESULTS=results_countonly

.PHONY: install figures check check-e8 experiments experiments-downlink experiments-bidirectional e8 e8-bidirectional measurements all clean

install:
	$(PY) -m pip install -r requirements.txt

# Regenerate the data figures from the saved results (pilot/results_countonly by default).
figures:
	cd figures && $(PY) make_figures.py && $(PY) make_fig_scale.py && $(PY) make_fig_defense_factorial.py

# Re-run every fast experiment for both observers into .check/ and compare with the stored files (read-only check).
check:
	cd pilot && $(PY) verify_results.py ../.check

# Exact re-runs of a fixed sample of stored E8 runs, for each observer.
check-e8:
	cd pilot && $(DOWN) $(PY) pilot2s_verify.py && $(PY) pilot2s_verify.py

# Recompute the stored result files in place.
experiments-downlink:
	cd pilot && for s in $(FAST); do echo "== $$s (downlink)"; $(DOWN) $(PY) $$s.py || exit 1; done
	cd pilot && $(DOWN) CYE_BG_NORM=der $(PY) pilot2c_sensitivity.py

experiments-bidirectional:
	cd pilot && for s in $(FAST) pilot2L_direction pilot2q_defense_factorial; do echo "== $$s (bidirectional)"; $(PY) $$s.py || exit 1; done
	cd pilot && CYE_BG_NORM=der $(PY) pilot2c_sensitivity.py

experiments: experiments-downlink experiments-bidirectional

# E8 (hours; resumable: runs already in pilot2s_scale.jsonl are skipped).
e8:
	cd pilot && $(DOWN) $(PY) pilot2s_scale.py && $(DOWN) $(PY) pilot2t_scale_analysis.py

e8-bidirectional:
	cd pilot && $(PY) pilot2s_scale.py && $(PY) pilot2t_scale_analysis.py

# Replaces the stored TLS measurements, loopback capture, and command-emission record with a new loopback run.
measurements:
	cd pilot && for s in real_tls_measure real_socket_capture pilot2p_hil; do echo "== $$s"; $(PY) $$s.py || exit 1; done

all: experiments figures

clean:
	rm -rf .check figures/figs/*.pdf
