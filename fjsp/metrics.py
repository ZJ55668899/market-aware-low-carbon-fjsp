"""Performance metrics: IGD (eq 14), C-metric (eq 15), HV (eq 16)."""
from __future__ import annotations

import math

from .nsga2 import dominates, fast_sort


def pareto_set(objs):
    """Indices of non-dominated solutions."""
    idx = []
    for i, a in enumerate(objs):
        if not any(dominates(b, a) for j, b in enumerate(objs) if j != i):
            idx.append(i)
    return idx


def igd(sol, ref):
    """Eq 14: mean over solution points of min distance to reference front."""
    if not sol or not ref:
        return math.nan
    tot = 0.0
    for s in sol:
        tot += min(math.dist(s, r) for r in ref)
    return tot / len(sol)


def c_metric(a, b):
    """Eq 15: fraction of B dominated by or equal to some member of A."""
    if not b:
        return math.nan
    cnt = 0
    for bb in b:
        for aa in a:
            if dominates(aa, bb) or all(abs(x - y) < 1e-9 for x, y in zip(aa, bb)):
                cnt += 1
                break
    return cnt / len(b)


def hv(sol, ref_point=None, normalize_by=None):
    """Eq 16, 3-D exact hypervolume via inclusion-exclusion over sorted slices.
    Objectives are minimized; ref_point defaults to per-objective max (paper)."""
    pts = [list(p) for p in sol]
    if not pts:
        return 0.0
    if normalize_by:
        pts = [[p[d] / normalize_by[d] for d in range(3)] for p in pts]
    if ref_point is None:
        ref_point = [max(p[d] for p in pts) * 1.0001 + 1e-9 for d in range(3)]
    keep = [p for p in pts if all(p[d] < ref_point[d] for d in range(3))]
    if not keep:
        return 0.0
    # exact 3D HV: sweep over sorted unique z-values
    keep.sort(key=lambda p: p[2])
    total = 0.0
    zs = sorted({p[2] for p in keep})
    for zi, z in enumerate(zs):
        z_next = zs[zi + 1] if zi + 1 < len(zs) else ref_point[2]
        dz = z_next - z
        if dz <= 0:
            continue
        layer = [p for p in keep if p[2] <= z + 1e-12]
        total += _area2d(layer, ref_point) * dz
    return total


def _area2d(pts, ref):
    """2D hypervolume (area) of minimized points against ref in dims 0,1:
    staircase sweep left-to-right."""
    if not pts:
        return 0.0
    pts = sorted(pts, key=lambda p: p[0])
    area = 0.0
    cur_y = ref[1]
    prev_x = None
    for p in pts:
        if p[1] < cur_y - 1e-12:
            if prev_x is not None:
                area += (min(p[0], ref[0]) - prev_x) * (ref[1] - cur_y)
            cur_y = p[1]
            prev_x = p[0]
    if prev_x is not None and cur_y < ref[1]:
        area += (ref[0] - prev_x) * (ref[1] - cur_y)
    return area
