"""C2 experiments: dynamic low-carbon FJSP, 3 rescheduling policies x scenarios.
Usage: python run_c2.py [n_scenarios] [runs_per_policy]"""
import json
import random
import statistics
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fjsp.dynamic import extend_instance, make_scenario, reschedule
from fjsp.instance import gear_shaft_instance
from fjsp.metrics import pareto_set
from fjsp.nsga2 import Config, run
from fjsp.schedule import StaticEnergyCostModel, decode

N_SCEN = int(sys.argv[1]) if len(sys.argv) > 1 else 8
RUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 4

inst = gear_shaft_instance()
model = StaticEnergyCostModel()
POLICIES = ["right-shift", "full", "incremental"]
records = {p: [] for p in POLICIES}

for s in range(N_SCEN):
    rng = random.Random(100 + s)
    cfg = Config(pop=100, gens=60, seed=900 + s, init="glr")
    pop, objs = run(inst, cfg)
    i = min(range(len(objs)), key=lambda k: objs[k][0])
    base = decode(inst, pop[i][0], pop[i][1])
    model.evaluate(inst, base)
    ev = make_scenario(inst, rng, n_break=1, n_rush=1)
    inst_eff, _ = extend_instance(inst, ev)
    for r in range(RUNS):
        cfg2 = Config(pop=100, gens=60, seed=5000 + 10 * s + r, init="glr")
        for pol in POLICIES:
            sch, stab, nrem = reschedule(inst_eff, base, ev, pol, cfg2, t=ev[0].time)
            records[pol].append(dict(scen=s, makespan=sch.makespan, cost=sch.cost,
                                     carbon=sch.carbon, stability=stab))
    print(f"scenario {s} done", flush=True)

summary = {}
for pol in POLICIES:
    rec = records[pol]
    summary[pol] = {
        "makespan_mean": round(statistics.mean(r["makespan"] for r in rec), 1),
        "cost_mean": round(statistics.mean(r["cost"] for r in rec), 1),
        "carbon_mean": round(statistics.mean(r["carbon"] for r in rec), 1),
        "stability_mean": round(statistics.mean(r["stability"] for r in rec), 1),
    }
    print(pol, summary[pol], flush=True)
with open("results/c2_results.json", "w") as f:
    json.dump(dict(summary=summary, records=records), f, indent=1)

fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
data_mk = [ [r["makespan"] for r in records[p]] for p in POLICIES ]
data_st = [ [r["stability"] for r in records[p]] for p in POLICIES ]
axes[0].boxplot(data_mk, tick_labels=POLICIES)
axes[0].set_ylabel("makespan (min)")
axes[0].set_title("rescheduling policies: makespan")
axes[1].boxplot(data_st, tick_labels=POLICIES)
axes[1].set_ylabel("stability (sum |shift| min)")
axes[1].set_title("schedule nervousness")
for ax in axes:
    ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("results/c2_policies.png", dpi=150)
print("c2 figures saved")
