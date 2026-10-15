"""Common-pool carbon price response (review R2-M2 identification fix).

Each price level is solved separately (finite budget), then for every run the
candidate schedules obtained at all prices (plus the flat-price baseline runs)
are pooled and re-evaluated at every price under the identical reality. The
minimum-cost selection from this common pool guarantees emissions non-increasing
in the carbon price, separating the true price response from search omission.
Usage: python run_c1_pricepool.py [inst] [runs]
"""
import json
import os
import statistics
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fjsp.c1_model import TOUSpeedCarbonModel, FlatUnifiedModel
from fjsp.instance import gear_shaft_instance, load_brandimarte
from fjsp.nsga2 import Config, run
from fjsp.schedule import decode

IN = sys.argv[1] if len(sys.argv) > 1 else "gear"
RUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 4
GENS = 80
PRICES = [0.0, 0.08, 0.8, 2.0]

plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
                     "legend.fontsize": 9})

inst = gear_shaft_instance() if IN == "gear" else load_brandimarte(f"instances/{IN}.fjs")
BASE_CFG = dict(init="glr", selection="tournament", rates="fixed", survival="standard")

# cap anchor from baseline runs
cap_pool = []
for r in range(RUNS):
    cfg = Config(pop=150, gens=GENS, seed=9000 + r, **BASE_CFG)
    pop, objs = run(inst, cfg, model=FlatUnifiedModel())
    cap_pool.extend(o[2] for o in objs)
CAP = statistics.median(cap_pool)

# solve per run per price, keep chromosomes
per_run = {r: {} for r in range(RUNS)}
for r in range(RUNS):
    cfgb = Config(pop=150, gens=GENS, seed=9100 + r, **BASE_CFG)
    popb, objb = run(inst, cfgb, model=FlatUnifiedModel())
    per_run[r]["BASE"] = [list(c) for c in popb]
    for pc in PRICES:
        m = TOUSpeedCarbonModel(tou=True, cap_trade=True, carbon_cap_kg=CAP,
                                carbon_price=pc)
        cfg = Config(pop=150, gens=GENS, seed=9200 + 10 * r + int(pc * 100),
                     use_speeds=True, **BASE_CFG)
        pop, objs = run(inst, cfg, model=m)
        per_run[r][pc] = [list(c) for c in pop]
    print("run", r, "solved", flush=True)


def evaluate(chrom, pc):
    m = TOUSpeedCarbonModel(tou=True, cap_trade=True, carbon_cap_kg=CAP,
                            carbon_price=pc)
    sp = chrom[2] if len(chrom) > 2 else None
    sch = decode(inst, chrom[0], chrom[1], sp)
    m.evaluate(inst, sch)
    return sch


res = {str(pc): {"cost": [], "cost_excl": [], "carbon": [], "makespan": []}
       for pc in PRICES}
for r in range(RUNS):
    pool = []
    for key in ["BASE"] + PRICES:
        pool.extend(per_run[r][key])
    for pc in PRICES:
        best = None
        for ch in pool:
            sch = evaluate(ch, pc)
            excl = sch.cost - sch.breakdown["settlement"]
            if best is None or sch.cost < best[0]:
                best = (sch.cost, excl, sch.carbon, sch.makespan)
        res[str(pc)]["cost"].append(round(best[0], 2))
        res[str(pc)]["cost_excl"].append(round(best[1], 2))
        res[str(pc)]["carbon"].append(round(best[2], 2))
        res[str(pc)]["makespan"].append(round(best[3], 2))

summary = {}
for pc in PRICES:
    summary[str(pc)] = {k: dict(mean=round(statistics.mean(v), 2),
                                sd=round(statistics.pstdev(v), 2))
                        for k, v in res[str(pc)].items()}
    print("pc", pc, summary[str(pc)], flush=True)
carbons = [summary[str(pc)]["carbon"]["mean"] for pc in PRICES]
mono = all(carbons[i + 1] <= carbons[i] + 1e-9 for i in range(len(carbons) - 1))
print("common-pool emissions non-increasing in price:", mono, flush=True)

out = dict(instance=IN, cap=CAP, runs=RUNS, per_price=summary,
           emissions_nonincreasing=mono)
with open(f"results/pricepool_{IN}.json", "w") as f:
    json.dump(out, f, indent=1)

fig, ax1 = plt.subplots(figsize=(6.6, 4.4))
means = [summary[str(pc)]["carbon"]["mean"] for pc in PRICES]
sds = [summary[str(pc)]["carbon"]["sd"] for pc in PRICES]
ax1.errorbar(PRICES, means, yerr=sds, marker="o", color="#2ca02c",
             label="carbon at common-pool min-cost selection")
ax1.set_xlabel("carbon price (CNY/kgCO2)")
ax1.set_ylabel("carbon (kgCO2)", color="#2ca02c")
ax1.tick_params(axis="y", labelcolor="#2ca02c")
ax2 = ax1.twinx()
mc = [summary[str(pc)]["cost_excl"]["mean"] for pc in PRICES]
sc = [summary[str(pc)]["cost_excl"]["sd"] for pc in PRICES]
ax2.errorbar(PRICES, mc, yerr=sc, marker="s", linestyle="--", color="#ff7f0e",
             label="cost excluding settlement")
ax2.set_ylabel("cost excl. settlement (CNY)", color="#ff7f0e")
ax2.tick_params(axis="y", labelcolor="#ff7f0e")
ax1.grid(alpha=0.3)
ax1.set_title(f"Common-pool carbon price response ({IN}), {RUNS} runs")
fig.tight_layout()
fig.savefig(f"results/rev2_pricepool_{IN}.png", dpi=300)
print("pricepool figure saved", flush=True)
