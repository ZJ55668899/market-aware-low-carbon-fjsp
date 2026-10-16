# Data and scenario provenance

`gear_shaft_case.json` records the processing alternatives, powers and material
costs transcribed from Table 3 of Mei et al., Machines 2024, 12(9), 590,
doi:10.3390/machines12090590. The same instance is embedded in `fjsp/instance.py`.
The base price 0.8118 CNY/kWh and emission factor 0.5703 kgCO2/kWh are reproduction
parameters adopted from that study's setting, not newly measured values.

The Brandimarte files provide processing alternatives/times only. Their energy
profiles are deterministic synthetic assumptions. All ten files here were
supplied in the author's development project. The original repository identifies
the TU/e "Job Shop Scheduling Benchmark Environments and Instances" collection
(GitHub organization ai-for-decision-making-tue, `data/fjsp/brandimarte/`) as a
public source for the Brandimarte family.

The tariff periods and multipliers, carbon price 0.08, wage rate 0.5, standby
ratio 0.2, startup energy equal to one idle minute and power-speed exponent 2
are scenario assumptions. No market-average or exact official tariff claim is
made for these values. Both idle power and startup energy scale with IDLE_RATIO.
The startup term denotes a loading transient at each busy-block start.

The rev3 archive mapping and derived data are documented in
[`docs/REV3_REPRODUCTION.md`](../docs/REV3_REPRODUCTION.md).
The grid emission factor is constant, so time shifting affects carbon through
changes in total electricity use rather than time-varying grid intensity.
