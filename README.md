# market-aware-low-carbon-fjsp

Companion code for the manuscript "Low-carbon flexible job-shop scheduling under
coupled electricity pricing, speed selection and carbon trading: tri-objective
optimization and the price-carbon conflict" (under review).

The repository implements a tri-objective flexible job-shop scheduling model that
integrates time-of-use (TOU) electricity pricing, discrete machine speed selection
and carbon cap-and-trade settlement, together with the flat-price constant-power
baseline model of Mei et al. (2024, Machines 12:590, doi:10.3390/machines12090590)
used for same-reality comparison. A dynamic extension with machine breakdowns,
rush-job insertions and three rescheduling policies is included in `fjsp/dynamic.py`.

## Layout

- `fjsp/` core package: instance parsing, decoding, objectives, solvers, metrics
  - `instance.py` Brandimarte parser, gear-shaft workshop case, energy parameters
  - `schedule.py` left-shift decoding and the static energy-cost model
  - `c1_model.py` market-aware model (TOU integral, power-speed law, cap-and-trade)
  - `nsga2.py` NSGA-II backbone, guided initialization, SA tournament, elite criterion
  - `dynamic.py` disruption events and right-shift / full / incremental rescheduling
  - `metrics.py` IGD, C-metric and exact 3-D hypervolume
- `examples/` experiment runners (Table 2 reproduction, case study, C1 and C2 experiments)
- `tests/` degradation check (market-aware model with mechanisms off reproduces the
  baseline term by term) and critical-path sanity test
- `instances/` three Brandimarte instances (see below)

## Quick start

Run all commands from the repository root. The revised protocol entry point is
`examples/run_c1_rev2.py`; the earlier `examples/run_c1.py` implements the first
round protocol with the processing-only electricity ledger and is kept for
traceability but superseded.

    pip install -r requirements.txt
    python tests/test_degradation.py        # mechanisms off == flat unified ledger
    python tests/test_decode_bounds.py      # decoder sanity
    python examples/run_c1_rev2.py gear 6 80   # unified-ledger main comparison
    python examples/run_c1_pricepool.py gear 4 # common-pool carbon price response
    python examples/run_c2.py 8 4           # disruption scenarios, three policies
    python examples/run_table2.py 20        # baseline algorithm reproduction (long run)

Results, per-run front archives and result hashes are written to `results/` and
`chaogai_output/` in the development workspace; the repository ships the summary
JSONs under `data/results/`.

## Headline results (unified ledger, revised protocol)

Same-reality evaluation with a pre-registered selection rule (minimum real-cost
point of the run-union non-dominated set), six runs of eighty generations per
model and instance, and a price-blind speed-aware control group:

| Instance | Flat-price baseline | Price-blind speed-aware control | Market-aware integrated model |
|---|---|---|---|
| Gear-shaft case | 437.1 min, 8488.6 CNY, 241.3 kgCO2 | 430.0 min, 8416.5 CNY, 255.2 kgCO2 | 406.2 min, 8396.9 CNY, 290.2 kgCO2 |
| Mk04 | 154.0 min, 166.4 CNY, 7.7 kgCO2 | 108.1 min, 147.4 CNY, 8.4 kgCO2 | 105.8 min, 145.1 CNY, 8.7 kgCO2 |

Per-run paired differences (integrated minus baseline) are minus 77.7 plus or
minus 13.6 CNY, minus 32.4 plus or minus 15.3 min and plus 33.3 plus or minus
14.4 kgCO2 on the workshop case, and minus 19.8 plus or minus 1.5 CNY, minus
37.5 plus or minus 6.8 min and plus 0.90 plus or minus 0.26 kgCO2 on Mk04. The
integrated schedule buys makespan and cost at a quantified carbon externality;
the common-pool carbon price sweep shows no discernible scheduling response at
the current proxy allowance price and a response onset between 0.08 and 0.8
CNY per kgCO2 at four-price resolution. Shift-origin experiments show that the
price-carbon trade-off sign depends on where the shift window sits against the
tariff profile, and the joint standby and start-stop zeroing experiment shows
that the trade-off channel varies with the instance.

## Reproduction note on the baseline algorithm

A component-wise reproduction of ASA-NSGA-EE from Mei et al. (2024) is included
(`examples/run_ablation.py`). Under faithful implementation the reported dominance
over plain NSGA-II does not reproduce on the Brandimarte family; the loss is
localized in the elite-retention criterion and the adaptive rate schedule, while
guided initialization is the consistently beneficial component. The solvers used
for the market-aware model keep guided initialization accordingly.

## Instances

`instances/` ships Mk01, Mk04 and Mk09 of the Brandimarte family. The complete
Mk01-Mk10 set is public benchmark data and can be downloaded from the TU/e
benchmark collection (Job Shop Scheduling Benchmark Environments and Instances,
ai-for-decision-making-tue on GitHub) under `data/fjsp/brandimarte/`.

## Citation

If you use this code, please cite the companion manuscript (under review) and the
baseline model paper:

    Mei Zheyu, Lu Yujun, Lv Liye. Research on multi-objective low-carbon flexible
    job shop scheduling based on improved NSGA-II. Machines, 2024, 12(9): 590.

## License

MIT, see LICENSE.
