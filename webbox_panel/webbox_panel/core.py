"""
Full WebBox / Sunny Island Modbus panel backend.

Three capabilities:
  1. Dashboard — the verified register map (confirmed live on the unit).
  2. Generic explorer — read ANY register/address with a chosen data type,
     so you can walk the SI table (manual section 5.4.8, addr ~47xx-56xx)
     and discover what your firmware actually exposes. Read is unrestricted.
  3. Guarded writes — known RW setpoints with clamp + FC16 + read-back verify,
     PLUS a raw write that is gated hard (must pass an explicit ack token and
     is refused for anything that looks like a battery-safety register unless
     it's in the clamped allow-list).

Data formats (SMA, big-endian / Motorola):
  U16/S16 = 1 reg, U32/S32 = 2 regs, U64/S64 = 4 regs.
  FIXn means value = raw / 10^n.
  NaN sentinels: 0xFFFF / 0xFFFFFFFF (unsigned), 0x8000 / 0x80000000 (signed).
"""

from __future__ import annotations
import inspect
import os
import time

from pymodbus.client import ModbusTcpClient

from . import registers as R
from . import writable as W

HOST = os.environ.get("WEBBOX_HOST", "192.168.100.180")
PORT = int(os.environ.get("WEBBOX_PORT", "502"))
UNIT = int(os.environ.get("WEBBOX_UNIT", "23"))
TIMEOUT = float(os.environ.get("WEBBOX_TIMEOUT", "5"))

# Raw writes require this token in the request, so nothing fires by accident.
RAW_WRITE_ACK = os.environ.get("RAW_WRITE_ACK", "")
GRID_GUARD_CODE = os.environ.get("GRID_GUARD_CODE", "")


def _kw(method) -> str:
    try:
        params = inspect.signature(method).parameters
    except (ValueError, TypeError):
        params = {}
    for n in ("device_id", "slave", "unit"):
        if n in params:
            return n
    return "device_id"


def client() -> ModbusTcpClient:
    return ModbusTcpClient(HOST, port=PORT, timeout=TIMEOUT)


# ---------------------------------------------------------------- typed decode

def decode_words(words: list[int], dtype: str, fix: int = 0):
    """Decode big-endian register words by SMA data type string."""
    n = {"U16": 1, "S16": 1, "U32": 2, "S32": 2, "U64": 4, "S64": 4}.get(dtype, 2)
    w = words[:n]
    u = 0
    for x in w:
        u = (u << 16) | (x & 0xFFFF)
    bits = 16 * n
    # NaN sentinels
    if dtype[0] == "U" and u == (1 << bits) - 1:
        return None
    if dtype[0] == "S" and u == 1 << (bits - 1):
        return None
    val = u - (1 << bits) if (dtype[0] == "S" and u >= 1 << (bits - 1)) else u
    return val / (10 ** fix) if fix else val


def regs_needed(dtype: str) -> int:
    return {"U16": 1, "S16": 1, "U32": 2, "S32": 2, "U64": 4, "S64": 4}.get(dtype, 2)


# ---------------------------------------------------------------- reads

def read_dashboard() -> dict:
    c = client()
    out = {}
    if not c.connect():
        return {"_error": f"cannot reach WebBox {HOST}:{PORT}"}
    try:
        rkw = _kw(ModbusTcpClient.read_holding_registers)
        for reg in R.DEFAULT_MAP:
            rr = c.read_holding_registers(reg.address, count=reg.count,
                                          **{rkw: UNIT})
            out[reg.name] = {
                "value": None if rr.isError() else R.decode_reg(reg, list(rr.registers)),
                "unit": reg.unit, "address": reg.address, "label": reg.ha_name,
            }
    finally:
        c.close()
    return out


def read_generic(address: int, dtype: str, fix: int, unit: int) -> dict:
    c = client()
    if not c.connect():
        return {"error": f"cannot reach WebBox {HOST}:{PORT}"}
    try:
        rkw = _kw(ModbusTcpClient.read_holding_registers)
        n = regs_needed(dtype)
        try:
            rr = c.read_holding_registers(address, count=n, **{rkw: unit})
        except (ValueError, OSError) as e:
            return {"error": f"read failed: {e}"}
        if rr.isError():
            return {"error": f"no response at {address} unit {unit} "
                    f"(wrong unit id, or register not on this profile)"}
        words = list(rr.registers)
        return {"address": address, "unit": unit, "dtype": dtype, "fix": fix,
                "words_hex": [f"{x:04x}" for x in words],
                "value": decode_words(words, dtype, fix)}
    finally:
        c.close()


# ---------------------------------------------------------------- writes

def write_known(param: str, value: float, confirm: bool, unit: int) -> dict:
    reg = W.WRITABLE.get(param)
    if reg is None:
        return {"error": f"unknown param {param}"}
    err = W.clamp_check(reg, value)
    if err:
        return {"error": err}
    c = client()
    if not c.connect():
        return {"error": f"cannot reach WebBox {HOST}:{PORT}"}
    try:
        rkw = _kw(ModbusTcpClient.read_holding_registers)
        wkw = _kw(ModbusTcpClient.write_registers)
        cur = c.read_holding_registers(reg.address, count=reg.count, **{rkw: unit})
        cur_val = None if cur.isError() else W.decode_wreg(reg, list(cur.registers))
        if not confirm:
            return {"dry_run": True, "param": param, "current": cur_val,
                    "requested": value, "unit": reg.unit, "note": reg.note,
                    "grid_guard_required": reg.grid_guard}

        # Grid Guard unlock first, if this register is protected
        if reg.grid_guard:
            if not GRID_GUARD_CODE:
                return {"error": "this setpoint is Grid Guard protected. Set "
                        "GRID_GUARD_CODE in the add-on config (your personal "
                        "SMA Grid Guard code) — the SI will silently ignore "
                        "the write without it."}
            try:
                code = int(GRID_GUARD_CODE)
                gg = W.encode_u32_be(code, 1)
                rr = c.write_registers(W.GRID_GUARD_REG, gg, **{wkw: unit})
                if rr.isError():
                    return {"error": f"Grid Guard unlock failed: {rr}"}
            except ValueError:
                return {"error": "GRID_GUARD_CODE must be numeric"}

        words = W.encode_value(reg, value)
        rr = c.write_registers(reg.address, words, **{wkw: unit})
        if rr.isError():
            return {"error": f"write failed: {rr}"}
        import time
        time.sleep(0.5)
        back = c.read_holding_registers(reg.address, count=reg.count, **{rkw: unit})
        back_val = None if back.isError() else W.decode_wreg(reg, list(back.registers))
        ok = back_val is not None and abs(back_val - value) <= max(reg.scale, 1)
        return {"param": param, "requested": value, "readback": back_val,
                "verified": ok, "unit": reg.unit,
                "grid_guard_used": reg.grid_guard,
                "warning": None if ok else "read-back mismatch — write may have "
                "been rejected (Grid Guard? value range? WebBox write support?)"}
    finally:
        c.close()


def write_raw(address: int, words: list[int], ack: str, confirm: bool,
              unit: int) -> dict:
    """Raw multi-register write. Hard-gated: needs the ack token, and refuses
    addresses inside the known battery-safety block unless they're in the
    clamped allow-list (which routes through write_known instead)."""
    if not RAW_WRITE_ACK:
        return {"error": "raw write disabled (set RAW_WRITE_ACK in add-on config "
                "to enable, then supply it as the ack)"}
    if ack != RAW_WRITE_ACK:
        return {"error": "bad ack token — raw write refused"}
    # protect the known safety registers from unclamped raw writes
    safety_addrs = {r.address for r in W.WRITABLE.values()}
    if address in safety_addrs:
        return {"error": f"address {address} is a clamped safety register — "
                f"use the guarded setpoint write, not raw"}
    if not confirm:
        return {"dry_run": True, "address": address, "words": words, "unit": unit}
    c = client()
    if not c.connect():
        return {"error": f"cannot reach WebBox {HOST}:{PORT}"}
    try:
        wkw = _kw(ModbusTcpClient.write_registers)
        rkw = _kw(ModbusTcpClient.read_holding_registers)
        rr = c.write_registers(address, words, **{wkw: unit})
        if rr.isError():
            return {"error": f"write failed: {rr}"}
        time.sleep(0.5)
        back = c.read_holding_registers(address, count=len(words), **{rkw: unit})
        bw = None if back.isError() else [f"{x:04x}" for x in back.registers]
        return {"address": address, "wrote": [f"{x:04x}" for x in words],
                "readback": bw, "unit": unit}
    finally:
        c.close()
