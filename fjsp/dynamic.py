"""C2 extension: dynamic low-carbon FJSP with machine breakdowns and rush jobs.

Policies compared at each disruption:
  right-shift : keep machine assignment & sequence of the baseline schedule,
                only delay operations conflicted by the breakdown (classical);
  full        : re-optimize every not-yet-completed operation from scratch;
  incremental : freeze operations already started, re-optimize the rest with a
                warm start (remaining-op sub-instance).
Stability (nervousness) = sum |start_new - start_old| over operations that had
not started at the event time.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from copy import deepcopy

from .instance import Instance, Op
from .nsga2 import Config, run
from .schedule import Schedule, StaticEnergyCostModel, decode, objectives


@dataclass
class Event:
    kind: str            # "breakdown" | "rush"
    time: float
    machine: int = -1
    duration: float = 0.0
    job_src: int = -1    # existing job copied for rush insertion


def estimate_horizon(inst):
    return (sum(min(t for _, t in op.alts) for op in inst.ops)
            / max(1, inst.n_machines) * 2.0)


def make_scenario(inst, rng, n_break=1, n_rush=1, horizon=None):
    """Assumption C2-a: breakdown start ~ U(0.2,0.6)H, duration ~ U(30,120) min;
    rush job = copy of a random existing job arriving at ~ U(0.2,0.5)H."""
    H = horizon or estimate_horizon(inst)
    ev = [Event("breakdown", rng.uniform(0.2 * H, 0.6 * H),
                machine=rng.randrange(inst.n_machines),
                duration=rng.uniform(30, 120))
          for _ in range(n_break)]
    ev += [Event("rush", rng.uniform(0.2 * H, 0.5 * H),
                 job_src=rng.randrange(inst.n_jobs))
           for _ in range(n_rush)]
    ev.sort(key=lambda e: e.time)
    return ev


def down_windows(events):
    return [(e.machine, e.time, e.time + e.duration)
            for e in events if e.kind == "breakdown"]


def extend_instance(inst, events):
    """Instance including rush jobs (copies of existing jobs)."""
    rush = [e.job_src for e in events if e.kind == "rush"]
    if not rush:
        return inst, {}
    ext = deepcopy(inst)
    map_new_job = {}
    for r, src in enumerate(rush):
        new_job = ext.n_jobs + r
        map_new_job[r] = new_job
        ext.job_ops.append([])
        ext.material_cost.append(ext.material_cost[src] if ext.material_cost else 0.0)
        for k, op_id in enumerate(inst.job_ops[src]):
            op = inst.ops[op_id]
            new_op = Op(job=new_job, idx=k, alts=list(op.alts))
            ext.ops.append(new_op)
            ext.op_power.append(dict(inst.op_power[op_id]) if inst.op_power else {})
            ext.job_ops[new_job].append(len(ext.ops) - 1)
        ext.n_jobs += 1
    return ext, map_new_job


def frozen_ops(inst, base_sched, t, completed_only=False):
    fixed = {}
    for op_id in range(len(base_sched.start)):
        started = base_sched.start[op_id] < t - 1e-9
        done = base_sched.end[op_id] <= t + 1e-9
        if (done if completed_only else started):
            fixed[op_id] = (base_sched.start[op_id], base_sched.end[op_id],
                            base_sched.machine_of[op_id])
    return fixed


def _sub_instance(inst, rem_ops, t):
    sub = Instance(name=inst.name + "_rem", n_jobs=inst.n_jobs,
                   n_machines=inst.n_machines)
    for attr in ("proc_power", "idle_power", "start_energy", "cost_rate",
                 "material_cost"):
        setattr(sub, attr, list(getattr(inst, attr)))
    sub.job_ops = [[] for _ in range(inst.n_jobs)]
    sub.op_power = []
    rem_set = set(rem_ops)
    sub_map = []                      # sub op id -> inst op id
    for j in range(inst.n_jobs):
        for op_id in inst.job_ops[j]:
            if op_id in rem_set:
                op = inst.ops[op_id]
                sub.ops.append(Op(job=j, idx=len(sub.job_ops[j]), alts=list(op.alts)))
                sub.op_power.append(dict(inst.op_power[op_id]) if inst.op_power else {})
                sub.job_ops[j].append(len(sub.ops) - 1)
                sub_map.append(op_id)
    return sub, sub_map


def _merge_eval(inst, sub, sub_map, chrom, fixed, down, t, model):
    """Greedy re-placement of the sub-solution on the full timeline honouring
    frozen ops, machine/job readiness and down windows; then evaluate."""
    n_ops = len(inst.ops)
    sch = Schedule(start=[0.0] * n_ops, end=[0.0] * n_ops, machine_of=[-1] * n_ops,
                   machine_busy=[0.0] * inst.n_machines,
                   machine_blocks=[0] * inst.n_machines, speeds=[1.0] * n_ops)
    mach_ready = [0.0] * inst.n_machines
    job_ready = [0.0] * inst.n_jobs
    for op_id, (s, e, m) in fixed.items():
        sch.start[op_id], sch.end[op_id], sch.machine_of[op_id] = s, e, m
        mach_ready[m] = max(mach_ready[m], e)
        job_ready[inst.ops[op_id].job] = max(job_ready[inst.ops[op_id].job], e)
        sch.machine_busy[m] += e - s
        sch.machine_blocks[m] += 1
    ptr = {j: 0 for j in range(inst.n_jobs)}
    for sub_id in range(len(sub.ops)):
        op_id = sub_map[sub_id]
        op = inst.ops[op_id]
        alt_idx = chrom[1][sub_id] % len(op.alts)
        m, tt = op.alts[alt_idx]
        s = max(t, mach_ready[m], job_ready[op.job])
        changed = True
        while changed:
            changed = False
            for (mm, ws, we) in down:
                if mm == m and s < we - 1e-9 and s + tt > ws + 1e-9:
                    s = we
                    changed = True
        e = s + tt
        sch.start[op_id], sch.end[op_id], sch.machine_of[op_id] = s, e, m
        mach_ready[m] = e
        job_ready[op.job] = e
        sch.machine_busy[m] += tt
        sch.machine_blocks[m] += 1
    sch.makespan = max(sch.end)
    model.evaluate(inst, sch)
    return sch


def reschedule(inst_eff, base_sched, events, policy, cfg, model=None, t=None,
               top_k=20):
    model = model or StaticEnergyCostModel()
    t = t if t is not None else events[0].time
    down = down_windows(events)
    completed = frozen_ops(inst_eff, base_sched, t, completed_only=True)
    if policy == "incremental":
        fixed = frozen_ops(inst_eff, base_sched, t, completed_only=False)
    elif policy == "full":
        fixed = completed
    else:                                   # right-shift: no re-optimization
        fixed = completed
    rem = [op_id for op_id in range(len(inst_eff.ops)) if op_id not in fixed]
    if policy == "right-shift":
        # keep original machine & job-chain order, delay as needed
        os_seq, ms_sel = [], []
        for op_id in rem:
            os_seq.append(inst_eff.ops[op_id].job)
        # ms index = position of baseline machine in op.alts
        ms_of = {}
        for op_id in rem:
            alts = inst_eff.ops[op_id].alts
            if op_id < len(base_sched.machine_of):
                m = base_sched.machine_of[op_id]
                idx = next((k for k, (mm, _) in enumerate(alts) if mm == m), 0)
            else:
                idx = 0          # rush job ops: keep first alternative
            ms_of[op_id] = idx
        sub, sub_map = _sub_instance(inst_eff, rem, t)
        sub_os, sub_ms = [], []
        for j in range(sub.n_jobs):
            for sid in sub.job_ops[j]:
                sub_os.append(j)
                sub_ms.append(ms_of[sub_map[sid]])
        sch = _merge_eval(inst_eff, sub, sub_map, (sub_os, sub_ms), fixed, down, t, model)
        return sch, _stability(base_sched, sch, t, rem), len(rem)
    sub, sub_map = _sub_instance(inst_eff, rem, t)
    if not sub.ops:
        sch = _merge_eval(inst_eff, sub, [], ([], []), fixed, down, t, model)
        return sch, 0.0, 0
    pop, objs = run(sub, cfg, model=model)
    order = sorted(range(len(objs)), key=lambda i: objs[i][0])[:top_k]
    best = None
    for i in order:
        sch = _merge_eval(inst_eff, sub, sub_map, pop[i], fixed, down, t, model)
        key = (sch.makespan, sch.cost, sch.carbon)
        if best is None or key < best[0]:
            best = (key, sch)
    return best[1], _stability(base_sched, best[1], t, rem), len(rem)


def _stability(old, new, t, rem):
    tot = 0.0
    for op_id in rem:
        if op_id < len(old.start) and old.start[op_id] >= t - 1e-9:
            tot += abs(new.start[op_id] - old.start[op_id])
    return tot
