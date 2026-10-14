"""C1 innovation experiments: TOU x speed x carbon cap-and-trade on top of the
reproduced baseline. Comparison logic (fair, same reality):
  E1  baseline schedule (static model, no speed layer) evaluated under the C1
      reality (TOU + trade, speeds fixed 1)  -> cost_real(base)
  E2  C1 model schedule (speed layer active) evaluated under same reality
      -> cost_real(C1); savings reported
  E3  self-ablation of C1 components (no-TOU / no-speed / no-trade)
  E4  sensitivity: carbon cap ratio x TOU spread
Usage: python run_c1.py <instance: gear|Mk04|Mk09> [runs] [gens]
"""
import json
import statistics
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fjsp.c1_model import TOUSpeedCarbonModel, TOU_MULTIPLIER
from fjsp.instance import gear_shaft_instance, load_brandimarte
from fjsp.metrics import pareto_set
from fjsp.nsga2 import Config, run
from fjsp.schedule import StaticEnergyCostModel, decode

IN = sys.argv[1] if len(sys.argv) > 1 else "gear"
RUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 8
GENS = int(sys.argv[3]) if len(sys.argv) > 3 else 100

inst = gear_shaft_instance() if IN == "gear" else load_brandimarte(f"instances/{IN}.fjs")
BASE_CFG = dict(init="glr", selection="tournament", rates="fixed", survival="standard")


def solve(model, use_speeds, runs=RUNS, gens=GENS):
    fronts = []
    for r in range(runs):
        cfg = Config(pop=150, gens=gens, seed=2000 + r, use_speeds=use_speeds, **BASE_CFG)
        pop, objs = run(inst, cfg, model=model)
        ps = pareto_set(objs)
        fronts.append(([pop[i] for i in ps], [objs[i] for i in ps]))
    return fronts


def reality_cost(chrom, speeds_on, cap=None):
    """Evaluate a chromosome under the C1 reality (TOU+trade, speed as encoded)."""
    m = TOUSpeedCarbonModel(tou=True, speeds=True, cap_trade=True,
                            carbon_cap_kg=CAP if cap is None else cap)
    sp = chrom[2] if speeds_on and len(chrom) > 2 else None
    sch = decode(inst, chrom[0], chrom[1], sp)
    if not speeds_on:
        sch.speeds = [1.0] * len(sch.speeds)
    m.evaluate(inst, sch)
    return sch


# ---- baseline solve (static model) ----
base_fronts = solve(StaticEnergyCostModel(), use_speeds=False)
base_union = [o for _, fr in base_fronts for o in fr]
cap_carbon = statistics.median(o[2] for o in base_union)
CAP = cap_carbon
print(f"[{IN}] baseline pareto union={len(base_union)}, carbon cap={CAP:.1f} kg")

# ---- C1 solve ----
c1_model = TOUSpeedCarbonModel(tou=True, speeds=True, cap_trade=True, carbon_cap_kg=CAP)
c1_fronts = solve(c1_model, use_speeds=True)

# ---- E1/E2: same-reality cost comparison at compromise (min-cost) solutions ----
def compromise(fronts, speeds_on):
    best = min((fr for _, fr in fronts), key=lambda fr: min(o[1] for o in fr))
    chroms = [ch for ch, fr in fronts if fr is best][0]
    i = min(range(len(best)), key=lambda k: best[k][1])
    return chroms[i]

ch_b = compromise(base_fronts, False)
ch_c = compromise(c1_fronts, True)
sch_b, sch_c = reality_cost(ch_b, False), reality_cost(ch_c, True)
sav = (sch_b.cost - sch_c.cost) / sch_b.cost * 100
for tag, sch in (("E1 base-under-reality", sch_b), ("E2 C1-under-reality", sch_c)):
    bd = getattr(sch, "breakdown", {})
    print(f"{tag}: mk={sch.makespan:.1f} cost={sch.cost:.0f} carbon={sch.carbon:.1f} | "
          f"material={bd.get('material',0):.0f} labor={bd.get('labor',0):.0f} "
          f"elec={bd.get('elec',0):.0f} settlement={bd.get('settlement',0):.0f}")
print(f"   -> total-cost saving of C1-aware optimization: {sav:.2f}%")

# ---- E3: component self-ablation (same-reality cost of each variant's compromise) ----
abl = {}
for name, kw, spd in [("full C1", dict(tou=True, speeds=True, cap_trade=True), True),
                      ("no-TOU", dict(tou=False, speeds=True, cap_trade=True), True),
                      ("no-speed", dict(tou=True, speeds=False, cap_trade=True), False),
                      ("no-trade", dict(tou=True, speeds=True, cap_trade=False), True)]:
    m = TOUSpeedCarbonModel(carbon_cap_kg=CAP, **kw)
    fr = solve(m, use_speeds=spd, runs=max(4, RUNS // 2))
    ch = compromise(fr, spd)
    sch = reality_cost(ch, spd)
    abl[name] = dict(makespan=round(sch.makespan, 1), cost=round(sch.cost, 1),
                     carbon=round(sch.carbon, 1))
    print(f"E3 {name:9s}: mk={sch.makespan:.1f} cost={sch.cost:.0f} carbon={sch.carbon:.1f}")

# ---- E4: sensitivity ----
sens = {}
for capr in (0.9, 1.0, 1.1):
    for spread, mult in [("flat", {"peak": 1.0, "flat": 1.0, "valley": 1.0}),
                         ("mild", {"peak": 1.3, "flat": 1.0, "valley": 0.6}),
                         ("wide", {"peak": 1.6, "flat": 1.0, "valley": 0.4})]:
        old = dict(TOU_MULTIPLIER)
        TOU_MULTIPLIER.update(mult)
        m = TOUSpeedCarbonModel(tou=True, speeds=True, cap_trade=True,
                                carbon_cap_kg=CAP * capr)
        fr = solve(m, use_speeds=True, runs=4, gens=max(60, GENS // 2))
        ch = compromise(fr, True)
        sch = reality_cost(ch, True, cap=CAP * capr)
        sens[f"cap{capr}/{spread}"] = dict(makespan=round(sch.makespan, 1),
                                           cost=round(sch.cost, 1),
                                           carbon=round(sch.carbon, 1))
        TOU_MULTIPLIER.clear(); TOU_MULTIPLIER.update(old)
        print(f"E4 cap×{capr} {spread:4s}: mk={sch.makespan:.1f} cost={sch.cost:.0f} carbon={sch.carbon:.1f}")

out = dict(instance=IN, cap=CAP,
           base_under_reality=dict(makespan=sch_b.makespan, cost=sch_b.cost, carbon=sch_b.carbon),
           c1_under_reality=dict(makespan=sch_c.makespan, cost=sch_c.cost, carbon=sch_c.carbon),
           saving_pct=round(sav, 2), ablation=abl, sensitivity=sens)
with open(f"results/c1_results_{IN}.json", "w") as f:
    json.dump(out, f, indent=1)

# ---- figures ----
fig, axes = plt.subplots(1, 3, figsize=(15, 4.3))
pairs = [(0, 1, "makespan", "total cost"), (0, 2, "makespan", "carbon"), (1, 2, "cost", "carbon")]
for ax, (a, b, la, lb) in zip(axes, pairs):
    rb = [reality_cost(ch, False) for ch in base_fronts[0][0]]
    rc = [reality_cost(ch, True) for ch in c1_fronts[0][0]]
    ax.scatter([getattr(s, ["makespan", "cost", "carbon"][a]) for s in rb],
               [getattr(s, ["makespan", "cost", "carbon"][b]) for s in rb],
               s=12, alpha=0.5, label="baseline model schedule")
    ax.scatter([getattr(s, ["makespan", "cost", "carbon"][a]) for s in rc],
               [getattr(s, ["makespan", "cost", "carbon"][b]) for s in rc],
               s=12, alpha=0.7, label="C1 model schedule")
    ax.set_xlabel(la); ax.set_ylabel(lb); ax.grid(alpha=0.3)
axes[0].legend(fontsize=8)
fig.suptitle(f"C1 vs baseline under identical TOU+trade reality ({IN})")
fig.tight_layout(); fig.savefig(f"results/c1_pareto_{IN}.png", dpi=150)

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
keys = list(sens.keys())
axes[0].plot(keys, [sens[k]["cost"] for k in keys], marker="o", label="total cost")
axes[0].set_ylabel("cost (yuan)"); axes[0].tick_params(axis="x", rotation=60)
axes[0].grid(alpha=0.3); axes[0].set_title("sensitivity: cap ratio x TOU spread")
axes[1].plot(keys, [sens[k]["carbon"] for k in keys], marker="s", color="g", label="carbon")
axes[1].set_ylabel("carbon (kg)"); axes[1].tick_params(axis="x", rotation=60)
axes[1].grid(alpha=0.3)
fig.tight_layout(); fig.savefig(f"results/c1_sensitivity_{IN}.png", dpi=150)
print(f"figures saved for {IN}")
