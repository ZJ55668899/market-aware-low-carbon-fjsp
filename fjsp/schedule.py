"""Decoding (chromosome -> schedule) and the three-objective evaluator.

The evaluator is parameterized by an EnergyCostModel so the C1 extension
(TOU tariff / speed levels / carbon cap-and-trade) can replace the base
static model without touching decoding or the algorithms.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .instance import CARBON_DELTA, ELEC_PRICE, Instance, SPEED_LEVELS


@dataclass
class Schedule:
    makespan: float = 0.0
    cost: float = 0.0
    carbon: float = 0.0
    start: list = field(default_factory=list)     # per op
    end: list = field(default_factory=list)       # per op
    machine_of: list = field(default_factory=list)  # per op
    machine_busy: list = field(default_factory=list)   # per machine total busy min
    machine_blocks: list = field(default_factory=list)  # per machine #busy blocks
    speeds: list = field(default_factory=list)          # per op speed factor (C1)


def decode(inst: Instance, os_seq, ms_sel, speeds=None) -> Schedule:
    """Left-shift (semi-active) decoding: place each op of os_seq on its chosen
    machine at the earliest feasible time. Assumption: the paper's 'active
    decoding' [ref 24] is implemented as left-shift, the standard practice in
    NSGA-II FJSP implementations."""
    n_ops = len(inst.ops)
    ptr = [0] * inst.n_jobs
    mach_ready = [0.0] * inst.n_machines
    mach_last_end = [-1e18] * inst.n_machines
    sch = Schedule(start=[0.0] * n_ops, end=[0.0] * n_ops, machine_of=[-1] * n_ops,
                   machine_busy=[0.0] * inst.n_machines,
                   machine_blocks=[0] * inst.n_machines,
                   speeds=[1.0] * n_ops)
    for jid in os_seq:
        k = ptr[jid]
        op_id = inst.job_ops[jid][k]
        ptr[jid] = k + 1
        op = inst.ops[op_id]
        alt_idx = ms_sel[op_id] % len(op.alts)
        m, t = op.alts[alt_idx]
        if speeds is not None:
            s = SPEED_LEVELS[speeds[op_id] % len(SPEED_LEVELS)]
            sch.speeds[op_id] = s
            t = t / s
        prev_end = sch.end[inst.job_ops[jid][k - 1]] if k > 0 else 0.0
        s = max(prev_end, mach_ready[m])
        e = s + t
        sch.start[op_id], sch.end[op_id], sch.machine_of[op_id] = s, e, m
        if s > mach_last_end[m] + 1e-9:
            sch.machine_blocks[m] += 1
        mach_last_end[m] = e
        mach_ready[m] = e
        sch.machine_busy[m] += t
    sch.makespan = max(sch.end) if n_ops else 0.0
    return sch


class StaticEnergyCostModel:
    """Base model of the target paper: constant machine power, flat electricity
    price, constant carbon factor. C1 replaces this class."""

    name = "static"

    def evaluate(self, inst: Instance, sch: Schedule):
        eproc = 0.0
        dproc = 0.0
        for op_id, op in enumerate(inst.ops):
            m = sch.machine_of[op_id]
            t = sch.end[op_id] - sch.start[op_id]
            pw = inst.op_power[op_id].get(m, inst.proc_power[m]) if inst.op_power else inst.proc_power[m]
            kwh = pw * t / 60.0
            eproc += kwh
            dproc += inst.cost_rate[m] * t + ELEC_PRICE * kwh
        eidle = 0.0
        for m in range(inst.n_machines):
            idle_min = max(0.0, sch.makespan - sch.machine_busy[m])
            eidle += inst.idle_power[m] * idle_min / 60.0
        ess = sum(inst.start_energy[m] * sch.machine_blocks[m]
                  for m in range(inst.n_machines))
        cost = sum(inst.material_cost) + dproc
        carbon = CARBON_DELTA * (eproc + eidle + ess)
        sch.cost, sch.carbon = cost, carbon
        return sch


def objectives(inst: Instance, os_seq, ms_sel, model=None, speeds=None) -> tuple:
    model = model or StaticEnergyCostModel()
    sch = decode(inst, os_seq, ms_sel, speeds)
    model.evaluate(inst, sch)
    return sch.makespan, sch.cost, sch.carbon
