# market-aware-low-carbon-fjsp

Companion code for the manuscript "Low-carbon flexible job-shop scheduling under
coupled electricity pricing, speed selection and carbon trading: tri-objective
optimization and the price-carbon conflict".

The repository implements a tri-objective flexible job-shop scheduling model that
integrates time-of-use (TOU) electricity pricing, discrete machine speed selection
and carbon cap-and-trade settlement, together with the flat-price constant-power
baseline model of Mei et al. (2024, Machines 12:590, doi:10.3390/machines12090590)
used for same-reality comparison.

## Layout

- `fjsp/` core package: instance parsing, decoding, objectives, solvers, metrics
- `examples/` experiment runners
- `tests/` degradation and sanity checks
- `instances/` three Brandimarte instances (see below)

## Quick start

Run all commands from the repository root.

    pip install -r requirements.txt
    python examples/run_case.py 6 80        # gear-shaft workshop case
    python examples/run_c1.py gear 6 80     # market-aware model vs baseline
    python tests/test_degradation.py        # mechanisms off == baseline model

## Instances

`instances/` ships Mk01, Mk04 and Mk09 of the Brandimarte family. The complete
Mk01-Mk10 set is public benchmark data and can be downloaded from the
TU/e benchmark collection (Job Shop Scheduling Benchmark Environments and
Instances, ai-for-decision-making-tue on GitHub) under `data/fjsp/brandimarte/`.
