"""MOGWO (Mirjalili et al. 2016) baseline for the paper's Table 2 third column.
Random-key encoding: continuous vectors in [-1,1]^(n_os+n_ms) -> OS sequence
(sorted keys over the job multiset) and MS indices (scaled to alternative index).
Archive of (position, objectives) with grid-crowding truncation; leaders
alpha/beta/delta drawn by roulette over archive crowding."""
from __future__ import annotations

import math
import random

from .metrics import pareto_set
from .schedule import objectives


def _decode_keys(inst, kos, kms):
    order = sorted(range(len(kos)), key=lambda i: kos[i])
    jobs_flat = [j for j in range(inst.n_jobs) for _ in inst.job_ops[j]]
    os_seq = [jobs_flat[i] for i in order]
    ms = []
    for op, x in zip(inst.ops, kms):
        n_alt = len(op.alts)
        ms.append(min(n_alt - 1, max(0, int((x + 1.0) / 2.0 * n_alt))))
    return os_seq, ms


def _roulette(crowd):
    inv = [1.0 / (c + 1e-9) for c in crowd]
    tot = sum(inv)
    r = random.random() * tot
    acc = 0.0
    for i, v in enumerate(inv):
        acc += v
        if acc >= r:
            return i
    return len(inv) - 1


def _grid_crowding(objs, n_div=10):
    lo = [min(o[d] for o in objs) for d in range(3)]
    hi = [max(o[d] for o in objs) for d in range(3)]
    cnt = {}
    cells = []
    for o in objs:
        cell = tuple(min(n_div - 1, int((o[d] - lo[d]) / max(1e-12, hi[d] - lo[d]) * n_div))
                     for d in range(3))
        cells.append(cell)
        cnt[cell] = cnt.get(cell, 0) + 1
    return [cnt[c] for c in cells]


def run_mogwo(inst, pop=150, gens=100, seed=0, model=None, archive_max=150):
    rng = random.Random(seed)
    n_os = sum(len(v) for v in inst.job_ops)
    dim = n_os + len(inst.ops)
    X = [[rng.uniform(-1, 1) for _ in range(dim)] for _ in range(pop)]
    objs = []
    for x in X:
        os_seq, ms = _decode_keys(inst, x[:n_os], x[n_os:])
        objs.append(objectives(inst, os_seq, ms, model))
    archive = []          # list of (x, obj)
    for g in range(gens):
        a = 2.0 - 2.0 * g / max(1, gens - 1)
        if archive:
            crowd = _grid_crowding([o for _, o in archive])
        for i in range(pop):
            if archive:
                lead_idx = [rng.choice(range(len(archive))) if rng.random() < 0.3
                            else _roulette(crowd) for _ in range(3)]
                leaders = [archive[k] for k in lead_idx]
            else:
                leaders = [(X[i], objs[i])] * 3
            new = []
            for d in range(dim):
                acc = 0.0
                for Lx, Lo in leaders:
                    r1, r2 = rng.random(), rng.random()
                    A = 2 * a * r1 - a
                    C = 2 * r2
                    D = abs(C * Lx[d] - X[i][d])
                    acc += Lx[d] - A * D
                new.append(max(-1.0, min(1.0, acc / 3.0)))
            if rng.random() < 0.1:
                new[rng.randrange(dim)] = rng.uniform(-1, 1)
            X[i] = new
            os_seq, ms = _decode_keys(inst, new[:n_os], new[n_os:])
            objs[i] = objectives(inst, os_seq, ms, model)
        combined = [o for _, o in archive] + objs
        comb_x = [x for x, _ in archive] + X
        cidx = pareto_set(combined)
        archive = [(comb_x[i], combined[i]) for i in cidx]
        if len(archive) > archive_max:
            crowd = _grid_crowding([o for _, o in archive])
            order = sorted(range(len(archive)), key=lambda k: -crowd[k])
            archive = [archive[k] for k in order[:archive_max]]
    return [o for _, o in archive]
