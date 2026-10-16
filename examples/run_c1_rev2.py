import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
"""Historical C1 revision 2 optimization runner (review M1-M6 driven).

For revision 3 archive-based reconstruction use examples/rebuild_rev3.py.
This historical runner does not export the original full chromosome archives.

Pre-registered rules:
  selection   : minimum total cost point of the run-union Pareto front after
                re-evaluation under the identical reality (same rule, all models)
  fronts      : run-union, re-evaluated under reality, re-filtered non-dominated
  statistics  : per-run paired differences (same seed), mean and stdev
  set evidence: C-metric both directions between re-evaluated union fronts
Models:
  BASE  flat-price unified ledger, no speed layer   (conventional planning rule)
  CTRL  flat-price unified ledger, speed layer on   (price-blind, speed-aware)
  C1    TOU billing + cap-and-trade, speed layer on (market-aware)
Experiments: E1 main comparison, E2 mechanism ablation, E3 carbon-price sweep,
E4 shift-origin timing discrimination, E5 idle-ratio boundary, E6 cap translation
invariance check.
Usage: python examples/run_c1_rev2.py <gear|Mk04|Mk09> [runs] [gens]
"""
import json
import statistics
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fjsp.c1_model import TOU_MULTIPLIER, TOUSpeedCarbonModel, FlatUnifiedModel
from fjsp.instance import gear_shaft_instance, load_brandimarte
from fjsp.metrics import c_metric, pareto_set
from fjsp.nsga2 import Config, run
from fjsp.schedule import decode

os.makedirs("results", exist_ok=True)
if "--check" in sys.argv:
    print("Imports OK; results directory ready; no optimization run")
    raise SystemExit(0)

IN = sys.argv[1] if len(sys.argv) > 1 else "gear"
RUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 6
GENS = int(sys.argv[3]) if len(sys.argv) > 3 else 80

plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
                     "legend.fontsize": 9, "xtick.labelsize": 9, "ytick.labelsize": 9})

inst = gear_shaft_instance() if IN == "gear" else load_brandimarte(f"instances/{IN}.fjs")
BASE_CFG = dict(init="glr", selection="tournament", rates="fixed", survival="standard")


def solve(model, use_speeds, runs, gens=GENS, origin=0.0, seed0=2000):
    fronts = []
    for r in range(runs):
        cfg = Config(pop=150, gens=gens, seed=seed0 + r, use_speeds=use_speeds, **BASE_CFG)
        pop, objs = run(inst, cfg, model=model)
        ps = pareto_set(objs)
        fronts.append(([pop[i] for i in ps], [objs[i] for i in ps]))
    return fronts


def reality_eval(chrom, speeds_on, cap, origin=0.0, price_tou=True, pc=0.08):
    m = TOUSpeedCarbonModel(tou=price_tou, cap_trade=True, carbon_cap_kg=cap,
                            carbon_price=pc, origin=origin)
    sp = chrom[2] if speeds_on and len(chrom) > 2 else None
    sch = decode(inst, chrom[0], chrom[1], sp)
    if not speeds_on:
        sch.speeds = [1.0] * len(sch.speeds)
        sch.op_power_kw = [inst.op_power[i].get(m2, inst.proc_power[m2])
                           if inst.op_power else inst.proc_power[m2]
                           for i, m2 in enumerate(sch.machine_of)]
    m.evaluate(inst, sch)
    return sch


def union_under_reality(fronts, speeds_on, cap, origin=0.0):
    pool = []
    for chs, _ in fronts:
        for ch in chs:
            sch = reality_eval(ch, speeds_on, cap, origin)
            pool.append((ch, (sch.makespan, sch.cost, sch.carbon), sch))
    objs = [p[1] for p in pool]
    idx = pareto_set(objs)
    return [pool[i] for i in idx]


def select(union):
    return min(union, key=lambda p: p[1][1])


# ---------- cap anchor from BASE run-union (model-objective space) ----------
base_fronts = solve(FlatUnifiedModel(), False, RUNS)
base_pool = [o for _, fr in base_fronts for o in fr]
CAP = statistics.median(o[2] for o in base_pool)
print(f"[{IN}] cap anchor = {CAP:.2f} kgCO2", flush=True)

out = {"instance": IN, "cap": CAP, "runs": RUNS, "gens": GENS}

# ---------- E6 cap translation invariance (deterministic check) ----------
c1_fronts = solve(TOUSpeedCarbonModel(tou=True, cap_trade=True, carbon_cap_kg=CAP), True, RUNS)
union_c1 = union_under_reality(c1_fronts, True, CAP)
invar = {}
for ratio in (0.9, 1.0, 1.1):
    costs = []
    for ch, obj, sch in union_c1:
        s2 = reality_eval(ch, True, CAP * ratio)
        costs.append(s2.cost)
    invar[str(ratio)] = costs
d01 = [b - a for a, b in zip(invar["1.0"], invar["0.9"])]
d12 = [b - a for a, b in zip(invar["1.1"], invar["1.0"])]
exp_shift = 0.08 * 0.1 * CAP
out["E6_cap_translation"] = dict(
    expected_shift_per_0p1=round(exp_shift, 4),
    observed_shift_09_to_10=[round(v, 4) for v in d01[:3]],
    observed_shift_10_to_11=[round(v, 4) for v in d12[:3]],
    pairwise_diff_invariant=all(abs((b1 - a1) - (b2 - a2)) < 1e-6
                                for a1, a2 in zip(invar["0.9"], invar["1.0"])
                                for b1, b2 in zip(invar["0.9"], invar["1.0"])))
print("E6 cap translation: shift per 0.1 cap =", round(exp_shift, 3),
      "CNY; pairwise cost differences invariant:",
      out["E6_cap_translation"]["pairwise_diff_invariant"], flush=True)

# ---------- E1 main comparison with CTRL ----------
models = {"BASE": (FlatUnifiedModel(), False),
          "CTRL_price-blind_speed-aware": (FlatUnifiedModel(), True),
          "C1_market-aware": (TOUSpeedCarbonModel(tou=True, cap_trade=True,
                                                  carbon_cap_kg=CAP), True)}
e1 = {}
unions = {}
for name, (mdl, spd) in models.items():
    fr = solve(mdl, spd, RUNS) if name != "C1_market-aware" else c1_fronts
    u = union_under_reality(fr, spd, CAP)
    unions[name] = u
    sel = select(u)
    per_run = []
    for chs, _ in fr:
        best = None
        for ch in chs:
            sch = reality_eval(ch, spd, CAP)
            key = sch.cost
            if best is None or key < best[0]:
                best = (key, sch)
        per_run.append(best[1])
    e1[name] = dict(
        selected=dict(makespan=round(sel[2].makespan, 1), cost=round(sel[2].cost, 1),
                      carbon=round(sel[2].carbon, 1)),
        per_run_cost=[round(s.cost, 1) for s in per_run],
        per_run_makespan=[round(s.makespan, 1) for s in per_run],
        per_run_carbon=[round(s.carbon, 1) for s in per_run],
        breakdown={k: round(v, 1) for k, v in sel[2].breakdown.items()
                   if k in ("material", "labor", "elec", "settlement")},
        tier_kwh={k: round(v, 1) for k, v in sel[2].breakdown.get("tier_kwh", {}).items()},
        energy_split=dict(proc=round(sel[2].breakdown["proc_kwh"], 1),
                          idle=round(sel[2].breakdown["idle_kwh"], 1),
                          ss=round(sel[2].breakdown["ss_kwh"], 1)),
        speed_hist=[sel[0][2].count(i) for i in range(3)] if spd else None,
        clock_span=[round(min(sel[2].start), 1), round(sel[2].makespan, 1)])
out["E1"] = e1
for a, b in [("C1_market-aware", "BASE"), ("C1_market-aware", "CTRL_price-blind_speed-aware"),
             ("CTRL_price-blind_speed-aware", "BASE")]:
    out.setdefault("E1_cmetric", {})[f"{a}>{b}"] = round(
        c_metric([p[1] for p in unions[a]], [p[1] for p in unions[b]]), 3)
    out["E1_cmetric"][f"{b}>{a}"] = round(
        c_metric([p[1] for p in unions[b]], [p[1] for p in unions[a]]), 3)
for name in models:
    print("E1", name, e1[name]["selected"], flush=True)
print("E1 C-metric:", out["E1_cmetric"], flush=True)


def _crosses(t0, t1):
    from fjsp.c1_model import _next_boundary
    b = _next_boundary(t0)
    return t1 > b + 1e-9


# ---------- E2 mechanism ablation ----------
e2 = {}
for name, kw, spd in [("full C1", dict(tou=True, cap_trade=True), True),
                      ("no-TOU", dict(tou=False, cap_trade=True), True),
                      ("no-speed", dict(tou=True, cap_trade=True), False),
                      ("no-trade", dict(tou=True, cap_trade=False), True)]:
    m = TOUSpeedCarbonModel(carbon_cap_kg=CAP, **kw)
    fr = solve(m, spd, RUNS)
    u = union_under_reality(fr, spd, CAP)
    sel = select(u)
    e2[name] = dict(makespan=round(sel[2].makespan, 1), cost=round(sel[2].cost, 1),
                    carbon=round(sel[2].carbon, 1),
                    energy_split=dict(proc=round(sel[2].breakdown["proc_kwh"], 1),
                                      idle=round(sel[2].breakdown["idle_kwh"], 1),
                                      ss=round(sel[2].breakdown["ss_kwh"], 1)))
    print("E2", name, e2[name], flush=True)
out["E2"] = e2

# ---------- E3 carbon price sweep ----------
e3 = {}
for pc in (0.0, 0.08, 0.8, 2.0):
    m = TOUSpeedCarbonModel(tou=True, cap_trade=True, carbon_cap_kg=CAP, carbon_price=pc)
    fr = solve(m, True, max(3, RUNS - 2))
    u = union_under_reality(fr, True, CAP, )
    # selection under the same pc reality
    pool = []
    for chs, _ in fr:
        for ch in chs:
            sch = reality_eval(ch, True, CAP, pc=pc)
            pool.append((sch.makespan, sch.cost, sch.carbon))
    idx = pareto_set(pool)
    sel = min((pool[i] for i in idx), key=lambda o: o[1])
    e3[str(pc)] = dict(makespan=round(sel[0], 1), cost=round(sel[1], 1),
                       carbon=round(sel[2], 1))
    print("E3 pc=", pc, e3[str(pc)], flush=True)
out["E3_price_sweep"] = e3

# ---------- E4 shift-origin timing discrimination ----------
e4 = {}
for origin in (0.0, 360.0, 480.0):
    for name, spd in [("BASE", False), ("C1", True)]:
        m = (FlatUnifiedModel() if name == "BASE" else
             TOUSpeedCarbonModel(tou=True, cap_trade=True, carbon_cap_kg=CAP,
                                 origin=origin))
        if name == "BASE":
            m.origin = origin  # reality-consistent flat price unaffected by origin
        fr = solve(m, spd, max(3, RUNS - 2), seed0=4000)
        u = union_under_reality(fr, spd, CAP, origin=origin)
        sel = select(u)
        sch = sel[2]
        n_cross = sum(1 for i in range(len(inst.ops))
                      if _crosses(sch.start[i] + origin, sch.end[i] + origin))
        e4[f"origin{int(origin)}/{name}"] = dict(
            makespan=round(sch.makespan, 1), cost=round(sch.cost, 1),
            carbon=round(sch.carbon, 1),
            tier_kwh={k: round(v, 1) for k, v in sch.breakdown.get("tier_kwh", {}).items()},
            ops_crossing_tariff_boundary=n_cross)
        print("E4", origin, name, e4[f"origin{int(origin)}/{name}"], flush=True)
out["E4_origins"] = e4

# ---------- E5 idle-ratio boundary ----------
import fjsp.instance as instmod
e5 = {}
orig_ratio = instmod.IDLE_RATIO
for ratio in (0.0, 0.1, 0.2):
    instmod.IDLE_RATIO = ratio
    inst2 = gear_shaft_instance() if IN == "gear" else load_brandimarte(f"instances/{IN}.fjs")
    saved = globals()["inst"]
    globals()["inst"] = inst2
    for spread, mult in [("flat", {"peak": 1.0, "flat": 1.0, "valley": 1.0}),
                         ("wide", {"peak": 1.6, "flat": 1.0, "valley": 0.4})]:
        old = dict(TOU_MULTIPLIER)
        TOU_MULTIPLIER.update(mult)
        cap2 = None
        bf = solve(FlatUnifiedModel(), False, 3, seed0=6000)
        cap2 = statistics.median(o[2] for _, fr in bf for o in fr)
        m = TOUSpeedCarbonModel(tou=True, cap_trade=True, carbon_cap_kg=cap2)
        fr = solve(m, True, 3, seed0=6000)
        u = union_under_reality(fr, True, cap2)
        sel = select(u)
        e5[f"idle{ratio}/{spread}"] = dict(makespan=round(sel[2].makespan, 1),
                                           cost=round(sel[2].cost, 1),
                                           carbon=round(sel[2].carbon, 1))
        print("E5", ratio, spread, e5[f"idle{ratio}/{spread}"], flush=True)
        TOU_MULTIPLIER.clear()
        TOU_MULTIPLIER.update(old)
    globals()["inst"] = saved
instmod.IDLE_RATIO = orig_ratio
out["E5_idle_boundary"] = e5

with open(f"results/c1_rev2_{IN}.json", "w") as f:
    json.dump(out, f, indent=1)

# ---------- figures ----------
fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.6))
pairs = [(0, 1, "makespan (min)", "total cost (CNY)"),
         (0, 2, "makespan (min)", "carbon (kgCO2)"),
         (1, 2, "total cost (CNY)", "carbon (kgCO2)")]
colors = {"BASE": "#7f7f7f", "CTRL_price-blind_speed-aware": "#2ca02c",
          "C1_market-aware": "#ff7f0e"}
for ax, (a, b, la, lb) in zip(axes, pairs):
    for name in models:
        pts = [p[1] for p in unions[name]]
        ax.scatter([p[a] for p in pts], [p[b] for p in pts], s=14, alpha=0.65,
                   color=colors[name], label=name)
    ax.set_xlabel(la)
    ax.set_ylabel(lb)
    ax.grid(alpha=0.3)
axes[0].legend(fontsize=8, loc="best")
fig.suptitle(f"Run-union Pareto fronts re-evaluated under the identical reality ({IN})")
fig.tight_layout()
fig.savefig(f"results/rev2_pareto_{IN}.png", dpi=300)

fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.4))
names = list(e2.keys())
for ax, key, lab in zip(axes, ("makespan", "cost", "carbon"),
                        ("makespan (min)", "total cost (CNY)", "carbon (kgCO2)")):
    vals = [e2[nm][key] for nm in names]
    axes_i = ax.bar(names, vals, color=["#ff7f0e", "#1f77b4", "#7f7f7f", "#2ca02c"])
    ax.set_ylabel(lab)
    ax.tick_params(axis="x", rotation=15)
    ax.grid(alpha=0.3, axis="y")
fig.suptitle(f"Mechanism contributions under identical reality ({IN})")
fig.tight_layout()
fig.savefig(f"results/rev2_mechanism_{IN}.png", dpi=300)

fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
spreads = ["flat", "wide"]
for ax, key, lab in zip(axes, ("cost", "carbon"), ("total cost (CNY)", "carbon (kgCO2)")):
    for ratio in (0.0, 0.1, 0.2):
        vals = [e5[f"idle{ratio}/{sp}"][key] for sp in spreads]
        ax.plot(spreads, vals, marker="o", label=f"idle ratio {ratio}")
    ax.set_ylabel(lab)
    ax.grid(alpha=0.3)
axes[0].legend(fontsize=8)
fig.suptitle(f"Idle-power boundary of the price-carbon trade-off ({IN})")
fig.tight_layout()
fig.savefig(f"results/rev2_idle_boundary_{IN}.png", dpi=300)
print("rev2 figures saved", flush=True)
