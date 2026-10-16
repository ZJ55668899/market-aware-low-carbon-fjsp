# Revision 3 reproduction guide

This package accompanies the revised Chinese manuscript. The core solver/model
and unchanged chromosome archives come from public commit
`81cdfd8751e27f31d2a619e24d493f61b09f917a` of
https://github.com/ZJ55668899/market-aware-low-carbon-fjsp.
The repository now includes the revision 3 reconstruction files. The original
standalone supplement is also available in
[FJSP_rev3_reproducibility.zip](supplement/FJSP_rev3_reproducibility.zip);
its README records the local delivery state before this GitHub synchronization.

## Rebuild numerical results without optimization

From the repository root (or the extracted standalone package root), with Python 3.9 or later, run

    python examples/rebuild_rev3.py

Only the Python standard library is needed for numerical reconstruction. The
program checks archive hashes, decodes every archived chromosome under its
reconstructed planning configuration, and verifies every original objective.
It then writes `data/results/rev3/` files with full float precision.

- `archive_mapping_gear.json`, `archive_mapping_Mk04.json` record every source
  entry's experiment, mechanism flags, tariff multipliers, carbon price/cap,
  shift origin and joint non-processing energy ratio. This mapping is recovered
  from the historical runner's call order and accepted only after all original
  planning objectives agree within 1e-6.
- `main_stats_rev3.json` contains selected chromosomes' source indices, all
  run-level main selections, paired differences, mean, population descriptive
  SD (denominator n), sample SD, paired t95 intervals (n=6, df=5), front vectors,
  both multiset and unique-vector coverage, and recomputed signed E6 shifts.
- `experiments_rev3.json` reconstructs E2 to E5 representative points.
- `pricepool_gear_rev3.json` contains every candidate's source index, unrounded
  non-settlement cost, carbon and makespan, plus every per-price selected ID,
  run-level output and mean/SD.

## Revision 3 common-pool protocol

For run r=0,1,2,3, pool the archived E1 BASE candidates and the four archived
E3 price fronts with the same run number. Their entry indices are
`12+r`, `48+r`, `52+r`, `56+r`, `60+r`. The four pools contain 749, 713, 744,
728 individuals, including duplicates. Reprice each FIXED pool at prices
0, 0.08, 0.8, 2.0 and select its minimum unrounded net-cost candidate. Exact
cost ties use first source order. The cap is 242.33292288069987 kgCO2.
This construction does not run any new optimization.

Carbon mean/SD_n by price is approximately
280.62796/7.59696, 280.62796/7.59696,
263.06441/10.70865, 239.97101/4.62642 kgCO2.
All four pools select the same candidate at prices 0 and 0.08. Monotonicity is
a fixed-pool linear-cost property, not evidence of a global or factory threshold.

The previous summary-only common-pool experiment used new seeds 9000/9100/9200.
It is preserved in `data/results/legacy_summary/pricepool_gear.json` for provenance
but is superseded for Table 5 and Figure 5. Do not mix its values (272.5 etc.)
with this archived-candidate protocol.

## Figures and existing checks

    pip install -r requirements.txt
    python examples/plot_rev3.py
    python tests/test_degradation.py
    python tests/test_decode_bounds.py
    python examples/run_c1_rev2.py --check
    python examples/run_c1_pricepool.py --check

Figure exports in `docs/figures/rev3/` include editable-text SVG, PDF and PNG.
The historical pricepool runner remains available with corrected import/output
setup, but its search protocol is not the rev3 archived-candidate pool. The old
rev2 runner is historical; it is not represented here as having generated the
original archives. The new `rebuild_rev3.py` explicitly documents their source
and regenerates the derived audit records from them.

## Source and limits

The two `archive_*.json` files are unchanged source data. Rounded legacy summary
arrays remain for traceability. E6 signed fields in the top-level rev2 summaries
are corrected; their originals are retained in `legacy_summary/`. Unrounded
revision 3 statistics take precedence over calculations on rounded legacy arrays.

`data/results/baseline_reproduction/` contains the author's existing per-instance
and component summary records and logs, copied from the development project.
Those are not a new rerun and do not include a complete per-generation archive.
All ten Brandimarte instance files supplied in that project are included for
reproduction. Their source is documented in `data/DATA.md`.

Tariff multipliers/time bands, carbon price, standby/startup convention, wage
rate and speed-power exponent are scenario assumptions. In particular 0.08 is
an illustrative internal carbon price, not an asserted 2024-2025 market average.
The case is not claimed to be an actual ETS compliance entity.

Repository snapshot hashes are listed in the root `MANIFEST_SHA256.json`. The
standalone ZIP has its own manifest for its original delivery snapshot.

To check the repository manifest from the repository root:

```bash
python -c "import hashlib,json,pathlib; r=pathlib.Path('.'); m=json.loads((r/'MANIFEST_SHA256.json').read_text(encoding='utf-8')); bad=[p for p,h in m.items() if not (r/p).is_file() or hashlib.sha256((r/p).read_bytes()).hexdigest()!=h]; print('Mismatches:',bad); raise SystemExit(bool(bad))"
```

The manifest covers supplied files and excludes itself, Git metadata, Python
caches and ignored runtime output. Check the supplied snapshot before
regeneration. Numerical outputs match the supplied JSON values under CPython
3.13; CPython 3.9 changes some sums at about 1e-12, within the 1e-6 objective
verification tolerance. Use numerical comparisons across runtime versions,
as regenerated hashes may differ. Figure export metadata can vary across
Matplotlib versions or regeneration times; check supplied figure hashes before
regenerating figures, and review regenerated figures visually.
