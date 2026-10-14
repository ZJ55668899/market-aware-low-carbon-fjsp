"""Degradation self-check (chaogai step 5 check 1): C1 model with extensions
switched off must reproduce the base static model exactly."""
import random

from fjsp.c1_model import TOUSpeedCarbonModel, FlatUnifiedModel
from fjsp.instance import gear_shaft_instance, load_brandimarte
from fjsp.nsga2 import make_chromosome, Config
from fjsp.schedule import StaticEnergyCostModel, decode

rng = random.Random(7)
for inst in (gear_shaft_instance(), load_brandimarte("instances/Mk01.fjs")):
    base, ext = FlatUnifiedModel(), TOUSpeedCarbonModel(tou=False, speeds=False,
                                                        cap_trade=False)
    worst = 0.0
    for _ in range(200):
        os_seq, ms = make_chromosome(inst, Config(init="glr"), rng)
        s1 = decode(inst, os_seq, ms)
        base.evaluate(inst, s1)
        o1 = (s1.makespan, s1.cost, s1.carbon)
        s2 = decode(inst, os_seq, ms)
        ext.evaluate(inst, s2)
        o2 = (s2.makespan, s2.cost, s2.carbon)
        worst = max(worst, max(abs(a - b) for a, b in zip(o1, o2)))
    print(f"{inst.name}: max abs deviation = {worst:.2e}")
    assert worst < 1e-9, "degradation check FAILED"
print("degradation self-check PASSED")
