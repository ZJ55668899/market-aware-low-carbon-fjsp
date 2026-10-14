"""Reproduce the gear-shaft enterprise case (sec 4.2, Fig 6/7): three variants,
convergence curves + Pareto scatter. Usage: python run_case.py [runs] [gens]"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fjsp.instance import gear_shaft_instance
from fjsp.metrics import pareto_set
from fjsp.nsga2 import Config, run

RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 10
GENS = int(sys.argv[2]) if len(sys.argv) > 2 else 100

VARIANTS = {
    "NSGA-II": dict(init="random", selection="tournament", rates="fixed", survival="standard"),
    "ASA-NSGA-EE(fixed rates)": dict(init="glr", selection="sa", rates="fixed", survival="elite_crit"),
    "ASA-NSGA-EE(adaptive rates)": dict(init="glr", selection="sa", rates="adaptive", survival="elite_crit"),
}

inst = gear_shaft_instance()
results = {}
for name, kw in VARIANTS.items():
    tracks, fronts = [], []
    for r in range(RUNS):
        cfg = Config(pop=150, gens=GENS, seed=100 + r, **kw)
        tr = []
        pop, objs = run(inst, cfg, track=tr)
        tracks.append(tr)
        ps = pareto_set(objs)
        fronts.append([objs[i] for i in ps])
    # mean convergence per objective
    import statistics
    conv = []
    for d in range(3):
        per_gen = [statistics.mean(tr[g][d] for tr in tracks) for g in range(GENS)]
        conv.append(per_gen)
    allf = [p for fr in fronts for p in fr]
    ps = pareto_set(allf)
    results[name] = {"convergence": conv, "pareto": [allf[i] for i in ps]}
    best = [min(p[d] for p in allf) for d in range(3)]
    print(f"{name}: best makespan={best[0]:.1f} min, cost={best[1]:.0f} yuan, carbon={best[2]:.1f} kg")

with open("results/case_results.json", "w") as f:
    json.dump(results, f)

fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
titles = ["(a) Makespan", "(b) Cost", "(c) Carbon emissions"]
for d, ax in enumerate(axes):
    for name in VARIANTS:
        ax.plot(results[name]["convergence"][d], label=name, lw=1.4)
    ax.set_title(titles[d])
    ax.set_xlabel("generation")
    ax.grid(alpha=0.3)
axes[0].legend(fontsize=8)
fig.suptitle("Gear-shaft case: convergence reproduction (paper Fig 6)")
fig.tight_layout()
fig.savefig("results/fig6_repro.png", dpi=150)

fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
pairs = [(0, 1, "makespan", "cost"), (0, 2, "makespan", "carbon"), (1, 2, "cost", "carbon")]
for ax, (a, b, la, lb) in zip(axes, pairs):
    for name in VARIANTS:
        pts = results[name]["pareto"]
        ax.scatter([p[a] for p in pts], [p[b] for p in pts], s=10, label=name, alpha=0.7)
    ax.set_xlabel(la)
    ax.set_ylabel(lb)
    ax.grid(alpha=0.3)
axes[0].legend(fontsize=8)
fig.suptitle("Gear-shaft case: Pareto fronts (paper Fig 7 projections)")
fig.tight_layout()
fig.savefig("results/fig7_repro.png", dpi=150)
print("figures saved")
