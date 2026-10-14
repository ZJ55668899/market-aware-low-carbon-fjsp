"""Reproduce paper Table 2: Mk01-10 x {NSGA-II, ASA-fixed, ASA-adaptive}.
Metrics per paper sec 4.1: IGD (eq14, ref = union Pareto over all runs/variants),
HV (eq16, normalized by ref per-objective max), C-metric (eq15) between variant
union Pareto sets. 20 runs x pop150 x gen100 as paper sec 4; best-of-runs recorded.
Usage: python run_table2.py [runs] [instances_csv]"""
import json
import statistics
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fjsp.instance import load_brandimarte
from fjsp.metrics import c_metric, hv, igd, pareto_set
from fjsp.mogwo import run_mogwo
from fjsp.nsga2 import Config, run

RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 20
INSTS = (sys.argv[2].split(",") if len(sys.argv) > 2
         else [f"Mk{i:02d}" for i in range(1, 11)])

VARIANTS = {
    "NSGA-II": dict(init="random", selection="tournament", rates="fixed", survival="standard"),
    "ASA-fix": dict(init="glr", selection="sa", rates="fixed", survival="elite_crit"),
    "ASA-adp": dict(init="glr", selection="sa", rates="adaptive", survival="elite_crit"),
}

table = {}
for iname in INSTS:
    inst = load_brandimarte(f"instances/{iname}.fjs")
    fronts = {}
    for vname, kw in VARIANTS.items():
        fr = []
        for r in range(RUNS):
            cfg = Config(pop=150, gens=100, seed=1000 + r, **kw)
            pop, objs = run(inst, cfg)
            ps = pareto_set(objs)
            fr.append([objs[i] for i in ps])
        fronts[vname] = fr
        print(f"{iname} {vname} done", flush=True)
    fr = []
    for r in range(RUNS):
        arch = run_mogwo(inst, pop=150, gens=100, seed=1000 + r)
        seen = set()
        ded = [tuple(round(v, 6) for v in o) for o in arch
               if tuple(round(v, 6) for v in o) not in seen
               and not seen.add(tuple(round(v, 6) for v in o))]
        fr.append([list(o) for o in ded])
    fronts["MOGWO"] = fr
    print(f"{iname} MOGWO done", flush=True)
    pool = [p for fr in fronts.values() for r in fr for p in r]
    refidx = pareto_set(pool)
    refraw = [pool[i] for i in refidx]
    lo = [min(p[d] for p in refraw) for d in range(3)]
    hi = [max(p[d] for p in refraw) for d in range(3)]
    span = [hi[d] - lo[d] if hi[d] - lo[d] > 1e-12 else 1.0 for d in range(3)]
    def nrm(pts):
        return [[(p[d] - lo[d]) / span[d] for d in range(3)] for p in pts]
    ref = nrm(refraw)
    row = {}
    unions = {}
    for vname, fr in fronts.items():
        union = [p for r in fr for p in r]
        pi = pareto_set(union)
        unions[vname] = [union[i] for i in pi]
        fr_n = [nrm(r) for r in fr]
        igds = [igd(r, ref) for r in fr_n]
        hvs = [hv(r, ref_point=(1.1, 1.1, 1.1)) for r in fr_n]
        row[vname] = dict(
            igd_best=round(min(igds), 4), igd_mean=round(statistics.mean(igds), 4),
            hv_best=round(max(hvs), 4), hv_mean=round(statistics.mean(hvs), 4))
    for a, b in [("ASA-fix", "NSGA-II"), ("NSGA-II", "ASA-fix"),
                 ("ASA-adp", "NSGA-II"), ("NSGA-II", "ASA-adp"),
                 ("ASA-fix", "ASA-adp"), ("ASA-adp", "ASA-fix"),
                 ("MOGWO", "NSGA-II"), ("ASA-fix", "MOGWO")]:
        row[f"C({a}>{b})"] = round(c_metric(unions[a], unions[b]), 3)
    table[iname] = row
    print(json.dumps({iname: row}), flush=True)

with open("results/table2_repro.json", "w") as f:
    json.dump(table, f, indent=1)

lines = ["| Inst | NSGA-II IGD/HV | ASA-fix IGD/HV | ASA-adp IGD/HV | MOGWO IGD/HV | C(ASAfix>NSGA) | C(NSGA>ASAfix) | C(ASAadp>NSGA) |",
         "|---|---|---|---|---|---|---|---|"]
for iname, row in table.items():
    lines.append(f"| {iname} | {row['NSGA-II']['igd_best']}/{row['NSGA-II']['hv_best']} | "
                 f"{row['ASA-fix']['igd_best']}/{row['ASA-fix']['hv_best']} | "
                 f"{row['ASA-adp']['igd_best']}/{row['ASA-adp']['hv_best']} | "
                 f"{row['MOGWO']['igd_best']}/{row['MOGWO']['hv_best']} | "
                 f"{row['C(ASA-fix>NSGA-II)']} | {row['C(NSGA-II>ASA-fix)']} | {row['C(ASA-adp>NSGA-II)']} |")
open("results/table2_repro.md", "w").write("\n".join(lines))
print("table2 done")
