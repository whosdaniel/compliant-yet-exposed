# Amendment 1a: scope correction to amendment 1 (revision R1)

**FROZEN 2026-10-28, before any count-only result of the control named below was computed.**
Amendment 1 (`prereg_amendment1_count_only.md`, SHA-256 `ecb31d17c0853fee9ac5c1075fb95c41691564b0f6292d3b46e415f274ee73be`)
stays unchanged. This file corrects one entry of its scope list.

## What was missed
Amendment 1 lists `pilot2g_mechanism.py` as not re-run "because comparing count and size is its purpose". That is true of its
part (B), the feature ablation, which clusters on count alone, size alone, and both, by design. Its part (A), the
temporal-shuffle control (real, same-fraction, and window-shuffle arms; reported in Section 6.1), is a mechanism control that
clusters on the observer's feature vector, which was `[z(count), z(size)]`. Under amendment 1 the primary observer sees the
count alone, so part (A) belongs in the re-run.

## When this was noticed
While mapping the manuscript's numbers to result files, after the count-only results of the 14 fast scripts of amendment 1 had
been computed (`pilot/results_countonly/`, 2026-10-28 20:03 KST) and while E8 was running. The decision to re-run part (A)
follows from the feature set it uses, not from any count-only result.

## Change
Part (A) of `pilot2g_mechanism.py` builds its features with the amendment-1 switch (`observed_features`); part (B) keeps its
explicit feature sets. Generators, seeds, and the clustering are unchanged. The same regression check applies first: with the
default features the modified script must reproduce the stored `pilot2g_mechanism.json` exactly. The count-only output goes
to `pilot/results_countonly/pilot2g_mechanism.json`, where part (B) is then identical to the stored file by construction.

## Not changed
`pilot2L_direction.py` and `pilot2q_defense_factorial.py` compare feature sets explicitly (downlink, uplink, bidirectional,
count alone; defenses crossed with count, size, and joint features) and stay as they are. Reporting follows amendment 1.
