"""C1 extension: TOU tariff x machine speed levels x carbon cap-and-trade.

Drop-in replacement for StaticEnergyCostModel. Degradation self-check:
flat multipliers = 1, single speed level, carbon price = 0  =>  identical
objectives to the base static model (asserted in test_degradation.py).
"""
from __future__ import annotations

from .instance import CARBON_DELTA, ELEC_PRICE, SPEED_LEVELS
from .schedule import Schedule, StaticEnergyCostModel

# Zhejiang-style industrial TOU multipliers on the flat base price (assumption C1-a)
TOU_MULTIPLIER = {"peak": 1.6, "flat": 1.0, "valley": 0.4}
# 24h cycle in minutes from shift start 0:00 (assumption C1-b)
TOU_PERIODS = [  # (start_min, end_min, tier)
    (0, 420, "valley"), (420, 480, "flat"), (480, 660, "peak"),
    (660, 780, "flat"), (780, 1140, "peak"), (1140, 1260, "flat"),
    (1260, 1380, "valley"), (1380, 1440, "valley"),
]
SPEED_POWER_EXP = 2.0               # P(s) = P0 * s^exp (assumption C1-c)
CARBON_PRICE = 0.08                 # yuan/kgCO2, national ETS proxy (assumption C1-d)


def _tier(t_min):
    m = t_min % 1440
    for a, b, tier in TOU_PERIODS:
        if a <= m < b:
            return tier
    return "flat"


def _price(t_min):
    return ELEC_PRICE * TOU_MULTIPLIER[_tier(t_min)]


class TOUSpeedCarbonModel:
    """Energy/cost model with time-of-use tariff, per-op speed choice and a
    carbon cap-and-trade settlement added to the cost objective."""
    name = "tou_speed_carbon"

    def __init__(self, tou=True, speeds=True, cap_trade=True,
                 carbon_cap_kg=None, carbon_price=CARBON_PRICE):
        self.tou, self.speeds, self.cap_trade = tou, speeds, cap_trade
        self.carbon_cap = carbon_cap_kg
        self.carbon_price = carbon_price

    def evaluate(self, inst, sch: Schedule):
        eproc = 0.0
        dproc = 0.0
        speeds = getattr(sch, "speeds", None) or [1.0] * len(inst.ops)
        for op_id, op in enumerate(inst.ops):
            m = sch.machine_of[op_id]
            t = sch.end[op_id] - sch.start[op_id]
            s = speeds[op_id] if self.speeds else 1.0
            pw0 = inst.op_power[op_id].get(m, inst.proc_power[m]) if inst.op_power \
                else inst.proc_power[m]
            pw = pw0 * (s ** SPEED_POWER_EXP)
            if self.tou:
                # integrate price over the op window (period boundaries inside window)
                kwh = 0.0
                tcur = sch.start[op_id]
                while tcur < sch.end[op_id] - 1e-9:
                    tier_end = self._next_boundary(tcur)
                    seg = min(tier_end, sch.end[op_id]) - tcur
                    kwh += pw * seg / 60.0 * (
                        _price(tcur) / ELEC_PRICE)  # kwh weighted by price multiplier
                    tcur += seg
                elec = kwh * ELEC_PRICE
                kwh_real = pw * t / 60.0
            else:
                kwh_real = pw * t / 60.0
                elec = kwh_real * ELEC_PRICE
            eproc += kwh_real
            dproc += inst.cost_rate[m] * t + elec
        eidle = 0.0
        for m in range(inst.n_machines):
            idle_min = max(0.0, sch.makespan - sch.machine_busy[m])
            eidle += inst.idle_power[m] * idle_min / 60.0
        ess = sum(inst.start_energy[m] * sch.machine_blocks[m]
                  for m in range(inst.n_machines))
        fe = eproc + eidle + ess
        carbon = CARBON_DELTA * fe
        cost = sum(inst.material_cost) + dproc
        if self.cap_trade and self.carbon_cap is not None:
            cost += self.carbon_price * (carbon - self.carbon_cap)
        sch.cost, sch.carbon = cost, carbon
        labor = sum(inst.cost_rate[sch.machine_of[i]] *
                    (sch.end[i] - sch.start[i]) for i in range(len(inst.ops)))
        sch.breakdown = dict(
            material=sum(inst.material_cost),
            labor=labor,
            elec=dproc - labor,
            settlement=(self.carbon_price * (carbon - self.carbon_cap)
                        if self.cap_trade and self.carbon_cap is not None else 0.0))
        return sch

    @staticmethod
    def _next_boundary(t):
        m = t % 1440
        for a, b, _ in TOU_PERIODS:
            if a <= m < b:
                return t - m + b
        return t - m + 1440


def degraded_model():
    """C1 model with all extensions switched off == base static model."""
    m = TOUSpeedCarbonModel(tou=False, speeds=False, cap_trade=False)
    return m
