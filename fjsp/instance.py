"""Instance model: Brandimarte .fjs parser, gear-shaft case (Table 3), energy params.

Energy/cost parameter slots are designed for the C1 extension (TOU tariff,
speed levels, carbon cap-and-trade): the evaluator consumes an EnergyCostModel
object, so swapping the base static model for C1 variants touches no decoder code.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Op:
    job: int
    idx: int                      # operation index within job
    alts: list                    # list of (machine, time_min)


@dataclass
class Instance:
    name: str
    n_jobs: int
    n_machines: int
    ops: list = field(default_factory=list)          # job-major list of Op
    job_ops: list = field(default_factory=list)      # job -> [op global ids]
    material_cost: list = field(default_factory=list)  # per job (yuan), 0 if n/a
    proc_power: list = field(default_factory=list)     # per machine kW (fallback)
    op_power: list = field(default_factory=list)       # per op: {machine: kW} or {}
    idle_power: list = field(default_factory=list)     # per machine kW
    start_energy: list = field(default_factory=list)   # per machine kWh/event
    cost_rate: list = field(default_factory=list)      # per machine yuan/min (labor)


def parse_fjs(path: str, name: str | None = None) -> Instance:
    with open(path, encoding="utf-8", errors="ignore") as f:
        toks = f.read().split()
    n_jobs, n_mach = int(toks[0]), int(toks[1])
    # header is "jobs machines [avg_machines_per_op]"; avg may be float (Mk02: 3.5)
    for header_len in (3, 2):
        try:
            inst = Instance(name=name or path.split("/")[-1],
                            n_jobs=n_jobs, n_machines=n_mach)
            inst.job_ops = [[] for _ in range(n_jobs)]
            inst.op_power = []
            _parse_jobs(inst, toks, header_len)
            return inst
        except (ValueError, IndexError):
            continue
    raise ValueError(f"unparseable .fjs: {path}")


def _parse_jobs(inst, toks, header_len):
    p = header_len
    n_jobs = inst.n_jobs
    for j in range(n_jobs):
        n_ops = int(toks[p]); p += 1
        for k in range(n_ops):
            n_alt = int(toks[p]); p += 1
            alts = []
            for _ in range(n_alt):
                m = int(toks[p]) - 1
                t = float(toks[p + 1])
                p += 2
                alts.append((m, t))
            op = Op(job=j, idx=k, alts=alts)
            inst.job_ops[j].append(len(inst.ops))
            inst.ops.append(op)
            inst.op_power.append({})
    return inst


# ---------------------------------------------------------------- gear shaft case
# Table 3 of Machines 2024, 12, 590 (job material cost; per op: machines, times, powers)
_GEAR = {
    1: (250, [([1, 2, 3], [10.8, 15, 11.7], [0.6, 0.88, 0.78]),
              ([1, 2, 3], [10, 7.5, 9.2], [0.6, 0.44, 0.6]),
              ([4, 5], [25.9, 30], [2.8, 3.3]),
              ([6, 7], [55.9, 51.7], [17.2, 14.5]),
              ([8], [5.8], [0.78]),
              ([9, 10], [23.4, 20], [8.8, 7])]),
    2: (500, [([1, 2, 3], [13.3, 12.5, 14.2], [0.8, 0.73, 0.95]),
              ([1, 2, 3], [11.7, 15, 13.3], [0.7, 0.9, 0.89]),
              ([4, 5], [27.5, 30.9], [3, 3.3]),
              ([6, 7], [43.4, 46.7], [13.6, 14.2]),
              ([8], [7.5], [0.1]),
              ([9, 10], [26.7, 25.9], [10, 9.1])]),
    3: (600, [([1, 2, 3], [18.3, 22.5, 20.9], [1, 1.3, 1.4]),
              ([1, 2, 3], [23.4, 25.9, 28.4], [1.4, 1.5, 1.9]),
              ([4, 5], [38.4, 33.4], [4.2, 3.6]),
              ([6, 7], [55.9, 62.6], [17.2, 17.4]),
              ([8], [6.7], [0.09]),
              ([9, 10], [34.2, 40.9], [12.8, 14.3])]),
    4: (700, [([1, 2, 3], [20, 23.4, 17.5], [1.17, 1.37, 1.17]),
              ([1, 2, 3], [21.7, 25.9, 18.3], [1.3, 1.5, 1.2]),
              ([4, 5], [35, 40.9], [3.8, 4.4]),
              ([11], [5], [1.0]),
              ([6, 7], [45, 48.4], [13.9, 13.3]),
              ([8], [5], [0.7]),
              ([10], [35], [12.3])]),
    5: (1850, [([1, 2, 3], [33.4, 36.7, 35], [1.9, 2.1, 2.34]),
               ([1, 2, 3], [39.2, 38.4, 39.2], [2.3, 2.24, 2.6]),
               ([4, 5], [48.4, 53.4], [5.2, 5.8]),
               ([11], [32.5], [6.5]),
               ([6, 7], [81.8, 90.1], [25.2, 24.8]),
               ([8], [5], [0.7]),
               ([9, 10], [148.46, 162.6], [55, 56.9])]),
    6: (1800, [([8], [9.2], [0.12]),
               ([1, 2, 3], [34.2, 40, 36.7], [1.99, 2.3, 2.45]),
               ([1, 2, 3], [30, 35, 30], [1.75, 2.04, 2.0]),
               ([4, 5], [16.7, 20.9], [1.8, 1.9]),
               ([11], [17.5], [3.5]),
               ([6, 7], [81.7, 86.7], [25.1, 23.8])]),
    7: (300, [([12, 13, 14, 15], [60, 61.7, 75.9, 80.1], [7.5, 7.7, 11.4, 12]),
              ([1, 2, 3], [15, 18.3, 14.2], [0.88, 1, 0.95]),
              ([1, 2, 3], [17.5, 21.7, 18.3], [1.02, 1.3, 1.2]),
              ([6, 7], [55.9, 61.7], [17.2, 17]),
              ([12, 13, 14, 15], [52.5, 55, 70.1, 67.6], [6.6, 6.89, 10.5, 10])]),
    8: (600, [([11], [12.5], [2.5]),
              ([1, 2, 3], [32.5, 38.4, 34.2], [1.9, 2.2, 2.28]),
              ([8], [18.3], [0.2]),
              ([1, 2, 3], [24.2, 27.5, 22.5], [1.4, 1.6, 1.5]),
              ([10], [8.3], [2.9]),
              ([12, 13, 14, 15], [94.2, 95.9, 67.6, 71.7], [11.8, 11.99, 10, 10.8])]),
    9: (600, [([6, 7], [75.9, 105.9], [23.4, 29.1]),
              ([1, 2, 3], [35.9, 38.4, 35], [2.1, 2.24, 2.3]),
              ([8], [25.9], [0.3]),
              ([1, 2, 3], [29.2, 30.9, 25.9], [1.7, 1.8, 1.7]),
              ([10], [8.3], [2.9]),
              ([12, 13, 14, 15], [103.4, 100.9, 65.9, 77.6], [12.9, 12.6, 9.88, 11.6])]),
    10: (200, [([6, 7], [81.7, 110.1], [25.2, 30.3]),
               ([1, 2, 3], [21.7, 24.2, 25.9], [1.27, 1.4, 1.7]),
               ([1, 2, 3], [26.7, 30.9, 27.5], [1.56, 1.8, 1.8])]),
}

SPEED_LEVELS = [0.8, 1.0, 1.2]   # C1 speed factors (assumption C1-c)
ELEC_PRICE = 0.8118       # yuan/kWh, Zhejiang industrial average (paper sec 4.2)
CARBON_DELTA = 0.5703     # kgCO2/kWh, national grid 2024 (paper sec 4.2)
WAGE_RATE = 0.5           # yuan/min labor rate -- assumption A5
IDLE_RATIO = 0.2          # idle power = ratio * proc power -- assumption A3/A4
START_MIN = 1.0           # start-stop energy = idle power * 1 min -- assumption A3/A4


def gear_shaft_instance() -> Instance:
    n_mach = 15
    inst = Instance(name="gear_shaft", n_jobs=len(_GEAR), n_machines=n_mach)
    inst.job_ops = [[] for _ in range(len(_GEAR))]
    inst.proc_power = [0.0] * n_mach
    for j in range(len(_GEAR)):
        cost, ops = _GEAR[j + 1]
        inst.material_cost.append(cost)
        for k, (machs, times, powers) in enumerate(ops):
            alts, pw_map = [], {}
            for m, t, pw in zip(machs, times, powers):
                alts.append((m - 1, t))
                pw_map[m - 1] = pw
                inst.proc_power[m - 1] = max(inst.proc_power[m - 1], pw)
            op = Op(job=j, idx=k, alts=alts)
            inst.job_ops[j].append(len(inst.ops))
            inst.ops.append(op)
            inst.op_power.append(pw_map)
    _fill_energy_params(inst)
    return inst


def _fill_energy_params(inst: Instance):
    m = inst.n_machines
    if not inst.proc_power or len(inst.proc_power) != m:
        # synthetic deterministic table for MK-family instances (assumption A3):
        base = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5,
                6.0, 7.0, 8.0, 10.0, 12.0, 14.0, 17.0, 20.0, 25.0, 30.0]
        inst.proc_power = [base[k % len(base)] for k in range(m)]
    inst.idle_power = [round(p * IDLE_RATIO, 4) for p in inst.proc_power]
    inst.start_energy = [round(p * IDLE_RATIO * START_MIN / 60.0, 6) for p in inst.proc_power]
    inst.cost_rate = [WAGE_RATE for _ in range(m)]


def load_brandimarte(path: str) -> Instance:
    inst = parse_fjs(path)
    inst.material_cost = [0.0] * inst.n_jobs
    _fill_energy_params(inst)
    return inst
