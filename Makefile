PY ?= python

.PHONY: install figures diagrams experiments all clean

install:
	$(PY) -m pip install -r requirements.txt

# Fast path: regenerate the data figures from the saved results in pilot/results.
figures:
	cd figures && $(PY) make_figures.py && $(PY) make_fig_defense_factorial.py

# Concept diagrams (Figures 1 to 3). Needs Chrome or Chromium; PNGs are already included.
diagrams:
	cd figures && $(PY) make_diagrams_svg.py

# Full reproduction: re-run every experiment (regenerates pilot/results), then the figures.
experiments:
	cd pilot && for s in real_tls_measure real_socket_capture pilot2_command_channel pilot2e_boundary pilot2i_metrics pilot2o_fig_ari pilot2c_sensitivity pilot2k_ari_curves pilot2n_drift pilot2j_wsweep pilot2q_defense_factorial pilot2b_correlation pilot2d_within_pool pilot2f_nuisance pilot2g_mechanism pilot2h_disaggregation pilot2L_direction pilot2m_psweep pilot2p_hil; do echo "== $$s =="; $(PY) $$s.py || exit 1; done

all: experiments figures

clean:
	rm -f figures/figs/*.png
