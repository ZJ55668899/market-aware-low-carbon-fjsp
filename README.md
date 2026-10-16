# market-aware-low-carbon-fjsp

Companion code and revision 3 materials for the Chinese manuscript
[耦合分时电价、变速选择与线性碳结算的柔性作业车间调度：三目标优化与价格碳权衡的情景依赖性](docs/manuscript/TOU_speed_carbon_FJSP_rev3_cn.docx).

The model integrates time-of-use (TOU) electricity pricing, discrete machine
speed selection and linear symmetric carbon settlement in tri-objective
flexible job-shop scheduling. A unified electricity ledger bills and counts
carbon from processing, internal idle gaps and busy-block startup transients.
The flat-price baseline follows Mei et al. (2024, *Machines* 12:590,
doi:10.3390/machines12090590). The repository also retains the earlier dynamic
rescheduling extension in `fjsp/dynamic.py`.

## Revision 3 documents and evidence

- [Chinese manuscript (Word)](docs/manuscript/TOU_speed_carbon_FJSP_rev3_cn.docx)
  and [searchable text](docs/manuscript/TOU_speed_carbon_FJSP_rev3_cn.md)
- [Third-round response (Word)](docs/manuscript/第三轮审稿回应与修改说明.docx)
  and [searchable text](docs/manuscript/第三轮审稿回应与修改说明.md)
- [Standalone reproducibility supplement](docs/supplement/FJSP_rev3_reproducibility.zip)
- [Reproduction guide](docs/REV3_REPRODUCTION.md),
  [change record](CHANGELOG_REV3.md) and [validation record](VALIDATION.md)
- [Unrounded reconstructed results](data/results/rev3/) and
  [seven figures in PNG, SVG and PDF](docs/figures/rev3/)

The text copies support searching and review; the DOCX files retain the native
equations and document layout. Author, affiliation and correspondence fields in
the manuscript still contain placeholders.

## Reproduce revision 3

Run from the repository root with Python 3.9 or later. Reconstruct the reported
numbers directly from the unchanged chromosome archives, without evolutionary
search or third-party Python packages:

```bash
python examples/rebuild_rev3.py
```

This checks both source archive hashes, reconstructs the experiment configuration
of every archive entry and verifies every original planning objective before
writing `data/results/rev3/`. To regenerate figures and run existing checks:

```bash
pip install -r requirements.txt
python examples/plot_rev3.py
python tests/test_degradation.py
python tests/test_decode_bounds.py
python examples/run_c1_rev2.py --check
python examples/run_c1_pricepool.py --check
```

The last two commands check the historical runners' import and output setup;
they do not regenerate the archived revision 3 common pool. The detailed guide
explains the pool construction, source indices, statistics and snapshot hashes.

## Main results and their scope

All three planning rules are evaluated under the same reality and electricity
ledger. The speed-aware control is price blind; C1 jointly senses TOU and carbon
settlement. Each cell below is the minimum-real-cost representative point of the
re-evaluated run-union front, in min / CNY / kgCO2. These points differ from
means of the six per-run selections.

| Instance | Flat-price BASE | Speed-aware CTRL | Integrated C1 |
|---|---|---|---|
| Gear-shaft case | 437.1 / 8488.6 / 241.3 | 430.0 / 8416.5 / 255.2 | 406.2 / 8396.9 / 290.2 |
| Mk04 | 154.0 / 166.4 / 7.7 | 108.1 / 147.4 / 8.4 | 105.8 / 145.1 / 8.7 |

Across six paired runs, C1 minus BASE gives cost −77.7 ± 13.6 CNY, makespan
−32.3 ± 15.3 min and carbon +33.3 ± 14.4 kgCO2 for the gear case; Mk04 gives
−19.8 ± 1.5 CNY, −37.5 ± 6.8 min and +0.90 ± 0.23 kgCO2. Here ± denotes
population descriptive SD (denominator n). The result JSON also supplies sample
SD, individual paired differences and sample-based t intervals.

The revised fixed pools combine archived E1 BASE candidates and four archived E3
price fronts within each of four runs. Prices 0 and 0.08 CNY/kgCO2 select the
same candidate in every pool; mean carbon decreases at the sampled prices 0.8
and 2.0. This is evidence within those finite pools and the stated search budget.
Shift-origin and joint idle/startup experiments show that the cost-carbon
trade-off varies with the tested instance and scenario. Linear symmetric
settlement makes the allowance cap an additive cost constant, so changing the
cap does not change schedule ranking under this model.

Tariff periods and multipliers, carbon price, wage, non-processing energy
conventions and the speed-power exponent are scenario assumptions. See
[data provenance](data/DATA.md); 0.08 is an illustrative internal carbon price.

## Repository layout

- `fjsp/`: instance parsing, queue-append decoding, objectives, solvers, metrics
  and dynamic rescheduling; core files are unchanged from commit `81cdfd8`
- `examples/rebuild_rev3.py`: numerical reconstruction from archived chromosomes
- `examples/plot_rev3.py`: revision 3 figure exports
- `examples/run_*.py`: retained historical optimization runners
- `tests/`: model degradation and critical-path bound checks
- `data/results/archive_*.json`: original chromosome archives
- `data/results/rev3/`: current unrounded statistics, configuration maps and pools
- `data/results/legacy_summary/`: original summaries retained for traceability
- `data/results/baseline_reproduction/`: supplied historical baseline summaries
  and logs; these do not include complete per-generation archives
- `instances/`: Brandimarte Mk01–Mk10 benchmark instances
- `docs/`: manuscript, response, supplement, figures and reproduction guide

## Historical experiments

The following commands start optimization and may take substantial time. Their
outputs go to ignored runtime directories such as `results/` and
`chaogai_output/`, as defined by the individual runner. They are retained for
further experiments; the offline reconstruction above is the entry point for
checking the revision 3 reported numbers.

```bash
python examples/run_c1_rev2.py gear 6 80
python examples/run_c1_pricepool.py gear 4
python examples/run_c2.py 8 4
python examples/run_table2.py 20
python examples/run_ablation.py
```

`run_c1.py` uses the earlier processing-only bill. `run_c1_rev2.py` uses the
unified ledger but does not export the original full chromosome archives.
`run_c1_pricepool.py` uses separate new-seed searches, a different protocol from
the archived-candidate revision 3 pool. Its original summary has moved to
`data/results/legacy_summary/pricepool_gear.json`.

The supplied baseline reproduction records show higher mean HV for plain
NSGA-II than ASA-fix on all ten Brandimarte instances; six reported coverage
values C(NSGA-II > ASA-fix) equal one. These are checks of existing records,
not a fresh twenty-run reproduction. Component results are retained in the
same directory for inspection.

## Citation and license

Please cite the companion manuscript and the baseline model paper:

> Mei Zheyu, Lu Yujun, Lv Liye. Research on multi-objective low-carbon flexible
> job shop scheduling based on improved NSGA-II. Machines, 2024, 12(9): 590.

The software is licensed under [MIT](LICENSE). Dataset provenance is documented
separately in [data/DATA.md](data/DATA.md).
