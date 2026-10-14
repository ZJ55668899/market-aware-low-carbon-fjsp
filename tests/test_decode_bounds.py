"""Sanity test: any feasible schedule respects the job-chain critical path bound."""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fjsp.instance import gear_shaft_instance
from fjsp.schedule import decode


def test_makespan_respects_critical_path_bound():
    inst = gear_shaft_instance()
    lb = sum(min(t for _, t in inst.ops[oid].alts) for oid in inst.job_ops[4])
    rng = random.Random(0)
    for _ in range(20):
        os_seq = [j for j in range(inst.n_jobs) for _ in inst.job_ops[j]]
        rng.shuffle(os_seq)
        ms = [rng.randrange(len(op.alts)) for op in inst.ops]
        sch = decode(inst, os_seq, ms)
        assert sch.makespan >= lb - 1e-6


if __name__ == "__main__":
    test_makespan_respects_critical_path_bound()
    print("critical-path bound test passed")
