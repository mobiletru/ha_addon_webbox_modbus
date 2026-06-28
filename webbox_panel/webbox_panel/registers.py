"""
Sunny Island read register map — from the live device map (FC03 holding regs).
Big-endian; SMA NaN sentinels (0xFF.. / 0x80..) decode to None.
"""
from __future__ import annotations
from dataclasses import dataclass

NAN_U32 = 0xFFFFFFFF
NAN_S32 = 0x80000000


@dataclass(frozen=True)
class Reg:
    name: str
    address: int
    count: int
    signed: bool
    scale: float
    unit: str
    ha_name: str
    device_class: str | None = None


DEFAULT_MAP: list[Reg] = [
    Reg("soc_pct",              30845, 2, False, 1,    "%",  "SOC", "battery"),
    Reg("battery_voltage_v",    30851, 2, False, 0.01, "V",  "Battery Voltage", "voltage"),
    Reg("battery_current_a",    30843, 2, True,  0.001,"A",  "Battery Current", "current"),
    Reg("battery_temp_c",       30849, 2, True,  0.1,  "°C", "Battery Temp", "temperature"),
    Reg("battery_capacity",     30847, 2, True,  1,    "",   "Battery Capacity", None),
    Reg("active_power_w",       30775, 2, True,  1,    "W",  "AC Power (+disch)", "power"),
    Reg("frequency_hz",         30803, 2, False, 0.01, "Hz", "Grid Frequency", "frequency"),
    Reg("grid_voltage_l1_v",    30783, 2, True,  0.01, "V",  "Grid Voltage L1", "voltage"),
    Reg("allowed_charge_power_w",   40189, 2, False, 1, "W", "Allowed Charge Power (BMS)", "power"),
    Reg("allowed_discharge_power_w",40191, 2, False, 1, "W", "Allowed Discharge Power (BMS)", "power"),
    Reg("charge_energy_wh",     30595, 2, False, 1,    "Wh", "Charge Energy (total)", "energy"),
    Reg("discharge_energy_wh",  30597, 2, False, 1,    "Wh", "Discharge Energy (total)", "energy"),
    Reg("batt_temp_min_c",      30997, 2, True,  0.1,  "°C", "Batt Temp Min (lifetime)", "temperature"),
    Reg("batt_temp_max_c",      30999, 2, True,  0.1,  "°C", "Batt Temp Max (lifetime)", "temperature"),
    Reg("batt_voltage_max_v",   31001, 2, True,  0.01, "V",  "Batt Voltage Peak (lifetime)", "voltage"),
    Reg("system_state",         30201, 2, False, 1,    "",   "System State", None),
]


def _block_to_int(regs: list[int], signed: bool) -> int:
    val = 0
    for r in regs:
        val = (val << 16) | (r & 0xFFFF)
    bits = 16 * len(regs)
    if signed and val >= (1 << (bits - 1)):
        val -= (1 << bits)
    return val


def decode_reg(reg: Reg, raw_regs: list[int]):
    uview = 0
    for r in raw_regs:
        uview = (uview << 16) | (r & 0xFFFF)
    bits = 16 * reg.count
    if reg.signed and uview == (1 << (bits - 1)):
        return None
    if (not reg.signed) and uview == (1 << bits) - 1:
        return None
    return round(_block_to_int(raw_regs, reg.signed) * reg.scale, 4)
