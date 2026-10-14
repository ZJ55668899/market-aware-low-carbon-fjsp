"""NSGA-II backbone and the ASA-NSGA-EE variant of Machines 2024, 12, 590.

Variants (config flags):
  init:        "random" | "glr"          (GLR ratios 0.6/0.3/0.1, sec 3.1)
  selection:   "tournament" | "sa"       (SA Metropolis tournament, sec 3.4 / Fig 3)
  rates:       "fixed" | "adaptive"      (eq 11-12 with k1=1,k2=0.9,k3=k4=0.05,c=0.6)
  survival:    "standard" | "elite_crit" (eq 13, Si=|Fi|*ri, ri~U(0.8,1))
ASA-NSGA-EE = glr + sa + adaptive + elite_crit; NSGA-II = random + tournament +
fixed + standard.  Fitness scalar for adaptive rates / SA (assumption A1):
f = 1/(1+rank) + normalized crowding distance.
"""
from __future__ import annotations

import math
import random

from .instance import SPEED_LEVELS
from .schedule import objectives

K1, K2, K3, K4, C_AD = 1.0, 0.9, 0.05, 0.05, 0.6
T0_SA = 0.3          # assumption A2 (accept ~0.5 at gen 0 for delta~0.2)


class Config:
    def __init__(self, pop=150, gens=100, pc=0.9, pm=0.2,
                 init="random", selection="tournament",
                 rates="fixed", survival="standard", seed=None, use_speeds=False):
        self.pop, self.gens, self.pc, self.pm = pop, gens, pc, pm
        self.init, self.selection, self.rates, self.survival = init, selection, rates, survival
        self.seed = seed
        self.use_speeds = use_speeds


def _rand(rng):
    return rng


def make_chromosome(inst, cfg, rng):
    os_seq = []
    for j in range(inst.n_jobs):
        os_seq.extend([j] * len(inst.job_ops[j]))
    rng.shuffle(os_seq)
    if cfg.init == "glr":
        ms = []
        for op in inst.ops:
            r = rng.random()
            if r < 0.6:      # GS: fastest machine
                m = min(op.alts, key=lambda a: a[1])
                ms.append(op.alts.index(m))
            elif r < 0.9:    # LS: fastest within random half subset (assumption)
                idxs = rng.sample(range(len(op.alts)), max(1, len(op.alts) // 2))
                best = min(idxs, key=lambda i: op.alts[i][1])
                ms.append(best)
            else:            # RS
                ms.append(rng.randrange(len(op.alts)))
    else:
        ms = [rng.randrange(len(op.alts)) for op in inst.ops]
    if cfg.use_speeds:
        return os_seq, ms, [rng.randrange(len(SPEED_LEVELS)) for _ in inst.ops]
    return os_seq, ms


def dominates(a, b):
    le = all(x <= y + 1e-12 for x, y in zip(a, b))
    lt = any(x < y - 1e-12 for x, y in zip(a, b))
    return le and lt


def fast_sort(objs):
    n = len(objs)
    rank = [0] * n
    fronts = [[]]
    dom_cnt = [0] * n
    dominated = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if dominates(objs[i], objs[j]):
                dominated[i].append(j)
                dom_cnt[j] += 1
            elif dominates(objs[j], objs[i]):
                dominated[j].append(i)
                dom_cnt[i] += 1
    cur = [i for i in range(n) if dom_cnt[i] == 0]
    for i in cur:
        rank[i] = 0
    while cur:
        nxt = []
        for i in cur:
            for j in dominated[i]:
                dom_cnt[j] -= 1
                if dom_cnt[j] == 0:
                    rank[j] = len(fronts)
                    nxt.append(j)
        fronts.append(nxt)
        cur = nxt
    fronts = [f for f in fronts if f]
    return rank, fronts


def crowding(objs, fronts):
    n = len(objs)
    cd = [0.0] * n
    for f in fronts:
        if len(f) <= 2:
            for i in f:
                cd[i] = math.inf
            continue
        for d in range(3):
            vals = sorted(f, key=lambda i: objs[i][d])
            lo, hi = objs[vals[0]][d], objs[vals[-1]][d]
            cd[vals[0]] = cd[vals[-1]] = math.inf
            rng = hi - lo
            if rng < 1e-12:
                continue
            for k in range(1, len(vals) - 1):
                cd[vals[k]] += (objs[vals[k + 1]][d] - objs[vals[k - 1]][d]) / rng
    return cd


def fitness_scalar(rank, cd):
    """Assumption A1: surrogate fitness for adaptive rates & SA tournament."""
    finite = [c for c in cd if c != math.inf]
    mx = max(finite) if finite else 1.0
    mx = mx if mx > 1e-12 else 1.0
    return [1.0 / (1.0 + r) + (0.0 if c == math.inf else c / mx) for r, c in zip(rank, cd)]


def ipox(os_a, os_b, rng):
    jobs = sorted(set(os_a))
    rng.shuffle(jobs)
    half = len(jobs) // 2
    g1, g2 = set(jobs[:half]), set(jobs[half:])
    o1 = [x if x in g1 else -1 for x in os_a]
    o2 = [x if x in g2 else -1 for x in os_b]
    c1, c2 = [], []
    q1 = [x for x in os_b if x in g2]   # holes of o1 are g2 occurrences -> fill from P2
    q2 = [x for x in os_a if x in g1]   # holes of o2 are g1 occurrences -> fill from P1
    p1 = p2 = 0
    for v in o1:
        if v != -1:
            c1.append(v)
        else:
            c1.append(q1[p1]); p1 += 1
    for v in o2:
        if v != -1:
            c2.append(v)
        else:
            c2.append(q2[p2]); p2 += 1
    return c1, c2


def ux(ms_a, ms_b, rng):
    r = [rng.random() < 0.5 for _ in range(len(ms_a))]
    c1 = [a if flag else b for a, b, flag in zip(ms_a, ms_b, r)]
    c2 = [b if flag else a for a, b, flag in zip(ms_a, ms_b, r)]
    return c1, c2


def mutate(chrom, inst, rng):
    os_c, ms_c = chrom[0], chrom[1]
    i, j = rng.sample(range(len(os_c)), 2)
    os_c[i], os_c[j] = os_c[j], os_c[i]
    i, j = rng.sample(range(len(ms_c)), 2)
    ms_c[i] = rng.randrange(len(inst.ops[i].alts))
    ms_c[j] = rng.randrange(len(inst.ops[j].alts))
    if len(chrom) > 2:
        i, j = rng.sample(range(len(chrom[2])), 2)
        chrom[2][i] = rng.randrange(len(SPEED_LEVELS))
        chrom[2][j] = rng.randrange(len(SPEED_LEVELS))
    return chrom


def _eval(inst, ch, model):
    if len(ch) > 2:
        return objectives(inst, ch[0], ch[1], model, speeds=ch[2])
    return objectives(inst, ch[0], ch[1], model)


def run(inst, cfg: Config, model=None, track=None):
    rng = random.Random(cfg.seed)
    pop = [make_chromosome(inst, cfg, rng) for _ in range(cfg.pop)]
    objs = [_eval(inst, ch, model) for ch in pop]
    history = []
    for g in range(cfg.gens):
        rank, fronts = fast_sort(objs)
        cd = crowding(objs, fronts)
        fit = fitness_scalar(rank, cd)
        fmax, fmean = max(fit), sum(fit) / len(fit)

        def pick():
            a, b = rng.randrange(len(pop)), rng.randrange(len(pop))
            if cfg.selection == "tournament":
                if rank[a] != rank[b]:
                    return a if rank[a] < rank[b] else b
                return a if cd[a] >= cd[b] else b
            # SA tournament (Fig 3): dominance decided by rank; ties -> Metropolis
            if rank[a] != rank[b]:
                return a if rank[a] < rank[b] else b
            better, worse = (a, b) if fit[a] >= fit[b] else (b, a)
            d = fit[better] - fit[worse]
            T = T0_SA * (1.0 - g / max(1, cfg.gens)) + 1e-9
            return worse if rng.random() < math.exp(-d / T) else better

        children = []
        while len(children) < cfg.pop:
            a, b = pick(), pick()
            if cfg.rates == "fixed":
                pc, pm = cfg.pc, cfg.pm
            else:
                fp = max(fit[a], fit[b])
                if fp > fmean and fmax > fmean + 1e-12:
                    pc = K1 * math.sin(C_AD / 2 * (fmax - fp) / (fmax - fmean))
                else:
                    pc = K2
                fm = min(fit[a], fit[b])
                if fm > fmean and fmax > fmean + 1e-12:
                    pm = K3 * math.sin(C_AD / 2 * (fmax - fm) / (fmax - fmean))
                else:
                    pm = K4
            if rng.random() < pc:
                o1, o2 = ipox(pop[a][0], pop[b][0], rng)
                m1, m2 = ux(pop[a][1], pop[b][1], rng)
                ch1, ch2 = [o1, m1], [o2, m2]
                if cfg.use_speeds:
                    s1, s2 = ux(pop[a][2], pop[b][2], rng)
                    ch1.append(s1); ch2.append(s2)
            else:
                ch1 = [list(x) for x in pop[a]]
                ch2 = [list(x) for x in pop[b]]
            for ch in (ch1, ch2):
                if rng.random() < pm:
                    mutate(ch, inst, rng)
                children.append(ch)
        children = children[:cfg.pop]
        cobjs = [_eval(inst, ch, model) for ch in children]
        combined = pop + children
        cobjs_all = objs + cobjs
        rank_c, fronts_c = fast_sort(cobjs_all)
        cd_c = crowding(cobjs_all, fronts_c)
        if cfg.survival == "standard":
            order = sorted(range(len(combined)), key=lambda i: (rank_c[i], -cd_c[i]))
            idx = order[:cfg.pop]
        else:
            idx, taken = [], set()
            for f in fronts_c:
                if len(idx) >= cfg.pop:
                    break
                r_i = rng.uniform(0.8, 1.0)
                s_i = int(len(f) * r_i)
                f_sorted = sorted(f, key=lambda i: -cd_c[i])
                sel = f_sorted[:min(s_i, cfg.pop - len(idx))]
                idx.extend(sel)
                taken.update(sel)
            if len(idx) < cfg.pop:
                rest = [i for i in range(len(combined)) if i not in taken]
                if cfg.survival == "elite_crit":      # literal sec 3.7: random fill
                    rng.shuffle(rest)
                    idx.extend(rest[:cfg.pop - len(idx)])
                else:                                  # elite_crit2: rank+crowding fill
                    rest.sort(key=lambda i: (rank_c[i], -cd_c[i]))
                    idx.extend(rest[:cfg.pop - len(idx)])
            idx = idx[:cfg.pop]
        pop = [combined[i] for i in idx]
        objs = [cobjs_all[i] for i in idx]
        if track is not None:
            track.append([min(o[d] for o in objs) for d in range(3)])
    return pop, objs
