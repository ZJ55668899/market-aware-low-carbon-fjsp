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

Run all commands from the repository root.

    pip install -r requirements.txt
    python tests/test_degradation.py        # mechanisms off == baseline model
    python tests/test_decode_bounds.py      # decoder sanity
    python examples/run_case.py 6 80        # gear-shaft workshop case
    python examples/run_c1.py gear 6 80     # market-aware model vs baseline
    python examples/run_c2.py 8 4           # disruption scenarios, three policies
    python examples/run_table2.py 20        # full Table 2 reproduction (long run)

Results (figures and JSON summaries) are written to `results/`.

## Headline results

Same-reality evaluation, i.e. every schedule settled under identical TOU and
cap-and-trade rules (6 runs x 80 generations on the workshop case, 6 runs x 80
generations on Mk04):

| Instance | Baseline flat-price schedule | Market-aware schedule |
|---|---|---|
| Gear-shaft case | 521.3 min, 8520 CNY, 411.0 kgCO2 | 369.3 min, 8363 CNY, 398.6 kgCO2 |
| Mk04 | 188.0 min, 165 CNY, 12.4 kgCO2 | 101.8 min, 145 CNY, 10.5 kgCO2 |

Component ablation under the same reality ranks the mechanisms as speed selection,
then TOU awareness, then cap-and-trade. Sensitivity analysis over cap ratios
(0.9, 1.0, 1.1) and peak-valley spreads (flat, mild, wide) shows the price-carbon
conflict: widening the spread from flat to wide lowers total cost by 2.7% while
raising carbon emissions by 7.3% through horizon extension and standby energy.

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
