"""Guarded Sunny Island writable setpoints (clamped + Grid Guard aware)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

GRID_GUARD_REG = 43090


@dataclass(frozen=True)
class WReg:
    name: str
    address: int
    count: int
    scale: float
    unit: str
    signed: bool
    vmin: float
    vmax: float
    grid_guard: bool
    note: str


WRITABLE: dict[str, WReg] = {
    "set_active_power": WReg(
        "set_active_power", 40149, 2, 1, "W", True,
        -6000, 6000, True,
        "power setpoint: NEGATIVE = charge, POSITIVE = discharge",
    ),
    "set_control_mode": WReg(
        "set_control_mode", 40151, 2, 1, "", False,
        0, 2000, True,
        "control mode selector (how power setpoints are interpreted)",
    ),
    "set_reactive_power": WReg(
        "set_reactive_power", 40153, 2, 1, "VAr", True,
        -6000, 6000, True,
        "reactive power setpoint for grid services",
    ),
    "min_soc_power_on": WReg(
        "min_soc_power_on", 40705, 2, 1, "%", False,
        0, 100, True,
        "minimum SOC required to power on the inverter",
    ),
    "min_soc_power_off": WReg(
        "min_soc_power_off", 40707, 2, 1, "%", False,
        0, 100, True,
        "SOC threshold at which the inverter shuts down",
    ),
}


def encode_value(reg: WReg, value: float) -> list[int]:
    raw = int(round(value / reg.scale))
    if reg.count == 2:
        if raw < 0:
            raw &= 0xFFFFFFFF
        return [(raw >> 16) & 0xFFFF, raw & 0xFFFF]
    if raw < 0:
        raw &= 0xFFFF
    return [raw & 0xFFFF]


def encode_u32_be(value: int, scale: float = 1) -> list[int]:
    raw = int(round(value / scale))
    if raw < 0:
        raw &= 0xFFFFFFFF
    return [(raw >> 16) & 0xFFFF, raw & 0xFFFF]


def clamp_check(reg: WReg, value: float) -> str | None:
    if value < reg.vmin or value > reg.vmax:
        return (
            f"refusing write: {value} {reg.unit} is outside the safe "
            f"range {reg.vmin}..{reg.vmax} {reg.unit} for {reg.name}"
        )
    return None


def decode_wreg(reg: WReg, raw_regs: list[int]):
    u = 0
    for r in raw_regs:
        u = (u << 16) | (r & 0xFFFF)
    bits = 16 * reg.count
    if reg.signed and u == 1 << (bits - 1):
        return None
    if (not reg.signed) and u == (1 << bits) - 1:
        return None
    val = u - (1 << bits) if (reg.signed and u >= 1 << (bits - 1)) else u
    return round(val * reg.scale, 4)


def writable_catalog() -> dict[str, Any]:
    return {
        k: {
            "address": v.address,
            "unit": v.unit,
            "min": v.vmin,
            "max": v.vmax,
            "note": v.note,
            "grid_guard": v.grid_guard,
        }
        for k, v in WRITABLE.items()
    }
