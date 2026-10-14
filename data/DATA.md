# Data

## What ships with the repository

- `gear_shaft_case.json` the real workshop case used in the manuscript: ten jobs,
  fifteen machines, per-pair processing times and measured processing powers, and
  the material cost of each job. Transcribed from Table 3 of Mei et al. (2024,
  Machines 12:590, doi:10.3390/machines12090590). The same values are embedded in
  `fjsp/instance.py` so the package runs without extra file handling; the JSON is
  the readable reference copy.
- `energy_parameters.json` every economic and energy parameter of the model in one
  place: base electricity price and TOU multipliers and period table, grid emission
  factor, allowance price, wage rate, idle-to-rated power ratio, start-up energy
  convention, speed levels and the power-speed exponent, plus the synthetic
  per-machine power profile used for the Brandimarte family.
- `../instances/` Mk01, Mk04 and Mk09 of the Brandimarte family in the standard
  `.fjs` format (processing times and machine alternatives only).

## What does not ship and where to get it

- The complete Brandimarte Mk01-Mk10 set is public benchmark data. Download it from
  the TU/e collection "Job Shop Scheduling Benchmark Environments and Instances"
  (GitHub organization ai-for-decision-making-tue) under `data/fjsp/brandimarte/`
  and drop the `.fjs` files into `../instances/`.
- No proprietary or personal data is used anywhere in this repository.

## Provenance and sync policy

- Measured quantities (times, powers, material costs of the workshop case) come from
  the published table of the baseline paper and are not modified here.
- Policy quantities (base price 0.8118 CNY/kWh, emission factor 0.5703 kgCO2/kWh)
  follow the official 2024 values cited in the baseline paper.
- Everything else is a documented modelling assumption of the manuscript (assumptions
  A3 to A5 and C1-a to C1-d): the synthetic power profile, the idle and start-up
  conventions, the wage rate, the TOU multiplier set and the allowance price. The
  constants live in `fjsp/instance.py` and `fjsp/c1_model.py`; `energy_parameters.json`
  mirrors them for readability. When editing one, update the other and run
  `python tests/test_degradation.py`, which fails if the market-aware model drifts
  from the baseline model under switched-off mechanisms.
