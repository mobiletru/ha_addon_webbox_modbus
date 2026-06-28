"""
Writable (RW) Sunny Island registers — corrected from the live device map.

Source: user's actual SI Modbus map (41 registers, 6 writable). These use
power setpoints + SOC thresholds, NOT a charge-stop voltage register.

IMPORTANT — Grid Guard:
  The protected setpoints (set_active_power, set_control_mode,
  set_reactive_power, min_soc_power_on/off) require the SMA Grid Guard
  unlock code to be written to register 43090 FIRST, in the same session.
  Without it the SI silently ignores the write. Grid Guard codes are
  personal/installer codes from SMA — not a generic value.

All writes here are clamped and read-back verified by the caller.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class WReg:
    name: str
    address: int
    count: int          # registers (2 for U32/S32)
    scale: float        # engineering = raw * scale
    unit: str
    signed: bool
    vmin: float
    vmax: float
    grid_guard: bool    # True if Grid Guard unlock required first
    note: str


GRID_GUARD_REG = 43090   # write the unlock code here before protected writes

WRITABLE: dict[str, WReg] = {
    "set_active_power": WReg(
        "set_active_power", 40149, 2, 1, "W", signed=True,
        vmin=-6000, vmax=6000, grid_guard=True,
        note="power setpoint: NEGATIVE = charge, POSITIVE = discharge"),
    "set_control_mode": WReg(
        "set_control_mode", 40151, 2, 1, "", signed=False,
        vmin=0, vmax=2000, grid_guard=True,
        note="control mode selector (how power setpoints are interpreted)"),
    "set_reactive_power": WReg(
        "set_reactive_power", 40153, 2, 1, "VAr", signed=True,
        vmin=-6000, vmax=6000, grid_guard=True,
        note="reactive power setpoint for grid services"),
    "min_soc_power_on": WReg(
        "min_soc_power_on", 40705, 2, 1, "%", signed=False,
        vmin=0, vmax=100, grid_guard=True,
        note="minimum SOC required to power on the inverter"),
    "min_soc_power_off": WReg(
        "min_soc_power_off", 40707, 2, 1, "%", signed=False,
        vmin=0, vmax=100, grid_guard=True,
        note="SOC threshold at which the inverter shuts down"),
}


def encode_value(reg: WReg, value: float) -> list[int]:
    """Engineering value -> big-endian registers (high word first)."""
    raw = int(round(value / reg.scale))
    if reg.count == 2:
        if raw < 0:
            raw &= 0xFFFFFFFF
        return [(raw >> 16) & 0xFFFF, raw & 0xFFFF]
    if raw < 0:
        raw &= 0xFFFF
    return [raw & 0xFFFF]


# back-compat alias used elsewhere
def encode_u32_be(value: float, scale: float) -> list[int]:
    raw = int(round(value / scale))
    if raw < 0:
        raw &= 0xFFFFFFFF
    return [(raw >> 16) & 0xFFFF, raw & 0xFFFF]


def clamp_check(reg: WReg, value: float) -> str | None:
    if value < reg.vmin or value > reg.vmax:
        return (f"refusing write: {value} {reg.unit} is outside the safe "
                f"range {reg.vmin}..{reg.vmax} {reg.unit} for {reg.name}")
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
