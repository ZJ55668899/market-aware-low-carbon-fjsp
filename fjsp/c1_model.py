"""Unified energy ledger and market-aware cost model (C1).

Ledger rules (review-driven revision M2): every kilowatt-hour that enters the
carbon account also enters the electricity bill.  Processing energy is billed
over the operation window, idle energy over internal machine gaps (machine ON
between its first and last operation), and start-stop energy at the instant a
busy block begins.  All three are integrated against the price function in
force, flat or time-of-use.  With mechanisms switched off this model reduces
term by term to FlatUnifiedModel (degradation test).

The [1]-faithful processing-only billing model stays in schedule.py
(StaticEnergyCostModel) and is used solely by the algorithm reproduction ladder.
"""
from __future__ import annotations

from .instance import CARBON_DELTA, ELEC_PRICE, SPEED_POWER_EXP
from .schedule import Schedule

# Zhejiang-style industrial TOU multipliers on the flat base price (assumption C1-a)
TOU_MULTIPLIER = {"peak": 1.6, "flat": 1.0, "valley": 0.4}
# 24h cycle in minutes (assumption C1-b)
TOU_PERIODS = [
    (0, 420, "valley"), (420, 480, "flat"), (480, 660, "peak"),
    (660, 780, "flat"), (780, 1140, "peak"), (1140, 1260, "flat"),
    (1260, 1440, "valley"),
]
CARBON_PRICE = 0.08                 # yuan/kgCO2, national ETS proxy (assumption C1-d)


def _tier(t_min):
    m = t_min % 1440
    for a, b, tier in TOU_PERIODS:
        if a <= m < b:
            return tier
    return "flat"


def _next_boundary(t):
    m = t % 1440
    for a, b, _ in TOU_PERIODS:
        if a <= m < b:
            return t - m + b
    return t - m + 1440


class UnifiedLedgerModel:
    """Full ledger with configurable price function and carbon settlement."""
    name = "unified"

    def __init__(self, tou=False, cap_trade=False, carbon_cap_kg=None,
                 carbon_price=CARBON_PRICE, origin=0.0):
        self.tou = tou
        self.cap_trade = cap_trade
        self.carbon_cap = carbon_cap_kg
        self.carbon_price = carbon_price
        self.origin = origin        # shift start clock, minutes (review M3)

    def price(self, t):
        if not self.tou:
            return ELEC_PRICE
        return ELEC_PRICE * TOU_MULTIPLIER[_tier(t + self.origin)]

    def _integrate(self, power_kw, t0, t1):
        """kWh and CNY over [t0,t1) at constant power under the price function."""
        kwh = cost = 0.0
        tiers = {}
        tc = t0
        while tc < t1 - 1e-9:
            if self.tou:
                bend = _next_boundary(tc + self.origin) - self.origin
            else:
                bend = t1
            seg = min(bend, t1) - tc
            if seg <= 1e-12:
                break
            e = power_kw * seg / 60.0
            kwh += e
            cost += e * self.price(tc)
            tier = _tier(tc + self.origin) if self.tou else "flat"
            tiers[tier] = tiers.get(tier, 0.0) + e
            tc += seg
        return kwh, cost, tiers

    def evaluate(self, inst, sch: Schedule):
        proc_kwh = proc_cost = 0.0
        tiers = {}
        for op_id in range(len(inst.ops)):
            m = sch.machine_of[op_id]
            if m < 0:
                continue
            t0, t1 = sch.start[op_id], sch.end[op_id]
            pw = sch.op_power_kw[op_id]
            k, c, tt = self._integrate(pw, t0, t1)
            proc_kwh += k
            proc_cost += c
            for key, v in tt.items():
                tiers[key] = tiers.get(key, 0.0) + v
        idle_kwh = idle_cost = 0.0
        for m in range(inst.n_machines):
            for (g0, g1) in sch.gaps[m]:
                k, c, tt = self._integrate(inst.idle_power[m], g0, g1)
                idle_kwh += k
                idle_cost += c
                for key, v in tt.items():
                    tiers[key] = tiers.get(key, 0.0) + v
        ss_kwh = ss_cost = 0.0
        for m in range(inst.n_machines):
            for bs in sch.block_starts[m]:
                k = inst.start_energy[m]
                ss_kwh += k
                ss_cost += k * self.price(bs)
        labor = sum(inst.cost_rate[sch.machine_of[i]] *
                    (sch.end[i] - sch.start[i]) for i in range(len(inst.ops))
                    if sch.machine_of[i] >= 0)
        fe = proc_kwh + idle_kwh + ss_kwh
        carbon = CARBON_DELTA * fe
        settlement = (self.carbon_price * (carbon - self.carbon_cap)
                      if self.cap_trade and self.carbon_cap is not None else 0.0)
        sch.cost = sum(inst.material_cost) + labor + proc_cost + idle_cost + ss_cost + settlement
        sch.carbon = carbon
        sch.breakdown = dict(
            material=sum(inst.material_cost), labor=labor,
            elec=proc_cost + idle_cost + ss_cost, settlement=settlement,
            proc_kwh=proc_kwh, idle_kwh=idle_kwh, ss_kwh=ss_kwh,
            tier_kwh=tiers)
        return sch


class FlatUnifiedModel(UnifiedLedgerModel):
    """Conventional planning rule: coherent flat-price ledger, no market mechanisms."""
    name = "flat-unified"

    def __init__(self):
        super().__init__(tou=False, cap_trade=False)


class TOUSpeedCarbonModel(UnifiedLedgerModel):
    """Market-aware model: TOU billing plus optional cap-and-trade settlement.
    Speed effects enter through the decoded schedule (op_power_kw, gaps)."""
    name = "tou_speed_carbon"

    def __init__(self, tou=True, speeds=True, cap_trade=True,
                 carbon_cap_kg=None, carbon_price=CARBON_PRICE, origin=0.0):
        super().__init__(tou=tou, cap_trade=cap_trade, carbon_cap_kg=carbon_cap_kg,
                         carbon_price=carbon_price, origin=origin)
        self.speeds = speeds        # informational: speeds live in the chromosome


def degraded_model():
    return TOUSpeedCarbonModel(tou=False, speeds=False, cap_trade=False)
