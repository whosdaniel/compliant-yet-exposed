# Revision records

This folder documents the first-round revision of the paper.

The three design files were written and frozen before the runs they govern:

- `prereg_E7_E8.md`: the design of E7 (unknown pool count) and E8 (fleet scale).
- `prereg_amendment1_count_only.md`: amendment 1, which moves the paper's results to the downlink observer (per-window record count).
- `prereg_amendment1a_scope.md`: amendment 1a, which adds the temporal-shuffle control to that re-run.

They are working records written with AI assistance, as declared in the paper. They were not deposited in an external registry. They are published unchanged so that their SHA-256 hashes, listed in the paper's supplementary material and in `SHA256SUMS`, can be checked:

```
shasum -a 256 -c SHA256SUMS      # or: sha256sum -c SHA256SUMS
```

Paths inside these records name the development tree (`reference/revision_r1/`); in this package the records are in `revision/` and the code is in `pilot/`.

Also here:

- `amendment1_regression_report.json`: before the downlink re-run, the modified scripts reproduced every stored result field with the original features.
- `precision_regen_report.json`, `precision_regen_pilot2L_report.json`: the regeneration of the result files with six stored decimals; every new value lies inside the rounding interval of the stored one.
- `diagnostics/`: post hoc checks cited in the paper and its supplementary material, each with its output.
