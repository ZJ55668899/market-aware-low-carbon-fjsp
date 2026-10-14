"""Component ablation: which ASA-NSGA-EE part helps/hurts? (reproduction forensics)"""
import json
import statistics
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fjsp.instance import gear_shaft_instance, load_brandimarte
from fjsp.metrics import hv, igd, pareto_set
from fjsp.nsga2 import Config, run

RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 8
GENS = int(sys.argv[2]) if len(sys.argv) > 2 else 100

VARIANTS = {
    "V0 NSGA-II (base)":            dict(init="random", selection="tournament", rates="fixed", survival="standard"),
    "V1 +GLR init":                 dict(init="glr", selection="tournament", rates="fixed", survival="standard"),
    "V2 +GLR+SA-tournament":        dict(init="glr", selection="sa", rates="fixed", survival="standard"),
    "V3 +GLR+SA+elite (=ASA-fix)":  dict(init="glr", selection="sa", rates="fixed", survival="elite_crit"),
    "V4 ASA adaptive rates":        dict(init="glr", selection="sa", rates="adaptive", survival="elite_crit"),
    "V5 +GLR+elite (no SA)":        dict(init="glr", selection="tournament", rates="fixed", survival="elite_crit"),
    "V6 elite_crit2 (rank fill)":   dict(init="glr", selection="sa", rates="fixed", survival="elite_crit2"),
}

insts = {"gear": gear_shaft_instance(),
         "Mk01": load_brandimarte("instances/Mk01.fjs"),
         "Mk04": load_brandimarte("instances/Mk04.fjs")}

out = {}
for iname, inst in insts.items():
    per = {}
    allfronts = {}
    for vname, kw in VARIANTS.items():
        fronts = []
        for r in range(RUNS):
            cfg = Config(pop=150, gens=GENS, seed=500 + r, **kw)
            pop, objs = run(inst, cfg)
            ps = pareto_set(objs)
            fronts.append([objs[i] for i in ps])
        allfronts[vname] = fronts
    refset = [p for v in allfronts.values() for fr in v for p in fr]
    refidx = pareto_set(refset)
    ref = [refset[i] for i in refidx]
    lo = [min(p[d] for p in ref) for d in range(3)]
    hi = [max(p[d] for p in ref) for d in range(3)]
    span = [hi[d] - lo[d] if hi[d] - lo[d] > 1e-12 else 1.0 for d in range(3)]
    def nrm(pts):
        return [[(p[d] - lo[d]) / span[d] for d in range(3)] for p in pts]
    ref = nrm(ref)
    for vname, fronts in allfronts.items():
        union = [p for fr in fronts for p in fr]
        best_mk = min(p[0] for p in union)
        fronts_n = [nrm(fr) for fr in fronts]
        hv_mean = statistics.mean(hv(fr, ref_point=(1.1, 1.1, 1.1)) for fr in fronts_n)
        igd_mean = statistics.mean(igd(fr, ref) for fr in fronts_n)
        per[vname] = dict(best_makespan=round(best_mk, 1), hv=round(hv_mean, 4), igd=round(igd_mean, 4))
        print(f"{iname:5s} {vname:30s} mk={best_mk:8.1f} HV={hv_mean:.4f} IGD={igd_mean:.4f}", flush=True)
    out[iname] = per

with open("results/ablation.json", "w") as f:
    json.dump(out, f, indent=1)
print("ablation done")
