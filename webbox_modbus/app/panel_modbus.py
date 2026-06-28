"""Modbus panel: live dashboard, register explorer, guarded + raw writes."""

from __future__ import annotations

import asyncio
import inspect
import time
from typing import Any

from pymodbus.client import ModbusTcpClient

from .live_registers import DEFAULT_MAP, decode_live_reg
from .panel_writable import (
    GRID_GUARD_REG,
    WRITABLE,
    clamp_check,
    decode_wreg,
    encode_u32_be,
    encode_value,
    writable_catalog,
)

_DTYPE_WORDS = {"U16": 1, "S16": 1, "U32": 2, "S32": 2, "U64": 4, "S64": 4}


def _unit_kw(method) -> str:
    try:
        params = inspect.signature(method).parameters
    except (ValueError, TypeError):
        params = {}
    for name in ("device_id", "slave", "unit"):
        if name in params:
            return name
    return "device_id"


def _client_for(webbox: dict[str, Any]) -> ModbusTcpClient:
    return ModbusTcpClient(
        webbox["host"],
        port=int(webbox.get("modbus_port") or 502),
        timeout=float(webbox.get("modbus_timeout") or 5),
    )


def _unit_id(webbox: dict[str, Any], override: int | None = None) -> int:
    if override is not None:
        return int(override)
    return int(webbox.get("modbus_unit_id") or 3)


def decode_words(words: list[int], dtype: str, fix: int = 0):
    n = _DTYPE_WORDS.get(dtype.upper(), 2)
    w = words[:n]
    u = 0
    for x in w:
        u = (u << 16) | (x & 0xFFFF)
    bits = 16 * n
    if dtype[0].upper() == "U" and u == (1 << bits) - 1:
        return None
    if dtype[0].upper() == "S" and u == 1 << (bits - 1):
        return None
    val = u - (1 << bits) if (dtype[0].upper() == "S" and u >= 1 << (bits - 1)) else u
    return val / (10**fix) if fix else val


def _read_live_dashboard(webbox: dict[str, Any]) -> dict[str, Any]:
    if not webbox.get("modbus_enabled", True):
        return {"online": False, "error": "Modbus disabled", "values": {}}

    client = _client_for(webbox)
    unit = _unit_id(webbox)
    host = webbox["host"]
    port = int(webbox.get("modbus_port") or 502)
    if not client.connect():
        return {"online": False, "error": f"cannot reach {host}:{port}", "values": {}}

    rkw = _unit_kw(ModbusTcpClient.read_holding_registers)
    values: dict[str, Any] = {}
    try:
        for reg in DEFAULT_MAP:
            rr = client.read_holding_registers(reg.address, count=reg.count, **{rkw: unit})
            values[reg.name] = {
                "value": None if rr.isError() else decode_live_reg(reg, list(rr.registers)),
                "unit": reg.unit,
                "address": reg.address,
                "label": reg.label,
            }
        return {"online": True, "host": host, "port": port, "unit_id": unit, "values": values}
    except Exception as exc:
        return {"online": False, "error": str(exc), "values": values}
    finally:
        client.close()


def _read_generic(
    webbox: dict[str, Any],
    address: int,
    dtype: str,
    fix: int,
    unit: int,
) -> dict[str, Any]:
    if not webbox.get("modbus_enabled", True):
        return {"error": "Modbus disabled for this WebBox"}

    dtype = dtype.upper()
    if dtype not in _DTYPE_WORDS:
        return {"error": f"unknown data type {dtype}"}
    if not (0 <= address <= 65533):
        return {"error": f"address {address} out of range (0-65533)"}
    if not (0 <= unit <= 247):
        return {"error": f"unit {unit} out of range (0-247)"}

    client = _client_for(webbox)
    host = webbox["host"]
    port = int(webbox.get("modbus_port") or 502)
    if not client.connect():
        return {"error": f"cannot reach {host}:{port}"}

    rkw = _unit_kw(ModbusTcpClient.read_holding_registers)
    n = _DTYPE_WORDS[dtype]
    try:
        rr = client.read_holding_registers(address, count=n, **{rkw: unit})
        if rr.isError():
            return {
                "error": f"no response at {address} unit {unit} "
                "(wrong unit id, or register not on this profile)",
            }
        words = list(rr.registers)
        return {
            "address": address,
            "unit": unit,
            "dtype": dtype,
            "fix": fix,
            "words_hex": [f"{x:04x}" for x in words],
            "value": decode_words(words, dtype, fix),
        }
    except (ValueError, OSError) as exc:
        return {"error": f"read failed: {exc}"}
    finally:
        client.close()


def _write_guarded(
    webbox: dict[str, Any],
    param: str,
    value: float,
    confirm: bool,
    unit: int,
    grid_guard_code: str,
) -> dict[str, Any]:
    reg = WRITABLE.get(param)
    if reg is None:
        return {"error": f"unknown param {param}"}
    err = clamp_check(reg, value)
    if err:
        return {"error": err}

    client = _client_for(webbox)
    host = webbox["host"]
    port = int(webbox.get("modbus_port") or 502)
    if not client.connect():
        return {"error": f"cannot reach {host}:{port}"}

    rkw = _unit_kw(ModbusTcpClient.read_holding_registers)
    wkw = _unit_kw(ModbusTcpClient.write_registers)
    try:
        cur = client.read_holding_registers(reg.address, count=reg.count, **{rkw: unit})
        cur_val = None if cur.isError() else decode_wreg(reg, list(cur.registers))
        if not confirm:
            return {
                "dry_run": True,
                "param": param,
                "current": cur_val,
                "requested": value,
                "unit": reg.unit,
                "note": reg.note,
                "grid_guard_required": reg.grid_guard,
            }

        if reg.grid_guard:
            if not grid_guard_code:
                return {
                    "error": "this setpoint is Grid Guard protected. Set grid_guard_code "
                    "in add-on Configuration — the SI silently ignores the write without it.",
                }
            try:
                code = int(grid_guard_code)
                gg = encode_u32_be(code)
                rr = client.write_registers(GRID_GUARD_REG, gg, **{wkw: unit})
                if rr.isError():
                    return {"error": f"Grid Guard unlock failed: {rr}"}
            except ValueError:
                return {"error": "grid_guard_code must be numeric"}

        words = encode_value(reg, value)
        rr = client.write_registers(reg.address, words, **{wkw: unit})
        if rr.isError():
            return {"error": f"write failed: {rr}"}
        time.sleep(0.5)
        back = client.read_holding_registers(reg.address, count=reg.count, **{rkw: unit})
        back_val = None if back.isError() else decode_wreg(reg, list(back.registers))
        ok = back_val is not None and abs(back_val - value) <= max(reg.scale, 1)
        return {
            "param": param,
            "requested": value,
            "readback": back_val,
            "verified": ok,
            "unit": reg.unit,
            "grid_guard_used": reg.grid_guard,
            "warning": None
            if ok
            else "read-back mismatch — write may have been rejected "
            "(Grid Guard? value range? WebBox write support?)",
        }
    finally:
        client.close()


def _write_raw(
    webbox: dict[str, Any],
    address: int,
    words: list[int],
    ack: str,
    confirm: bool,
    unit: int,
    raw_write_ack: str,
) -> dict[str, Any]:
    if not raw_write_ack:
        return {
            "error": "raw write disabled (set raw_write_ack in add-on Configuration, "
            "then supply it as the ack token)",
        }
    if ack != raw_write_ack:
        return {"error": "bad ack token — raw write refused"}

    safety_addrs = {r.address for r in WRITABLE.values()}
    if address in safety_addrs:
        return {
            "error": f"address {address} is a clamped safety register — "
            "use the guarded setpoint write, not raw",
        }
    if not confirm:
        return {"dry_run": True, "address": address, "words": words, "unit": unit}

    client = _client_for(webbox)
    host = webbox["host"]
    port = int(webbox.get("modbus_port") or 502)
    if not client.connect():
        return {"error": f"cannot reach {host}:{port}"}

    rkw = _unit_kw(ModbusTcpClient.read_holding_registers)
    wkw = _unit_kw(ModbusTcpClient.write_registers)
    try:
        rr = client.write_registers(address, words, **{wkw: unit})
        if rr.isError():
            return {"error": f"write failed: {rr}"}
        time.sleep(0.5)
        back = client.read_holding_registers(address, count=len(words), **{rkw: unit})
        bw = None if back.isError() else [f"{x:04x}" for x in back.registers]
        return {
            "address": address,
            "wrote": [f"{x:04x}" for x in words],
            "readback": bw,
            "unit": unit,
        }
    finally:
        client.close()


async def read_live_dashboard(webbox: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(_read_live_dashboard, webbox)


async def read_generic_register(
    webbox: dict[str, Any],
    address: int,
    dtype: str,
    fix: int,
    unit: int | None = None,
) -> dict[str, Any]:
    return await asyncio.to_thread(
        _read_generic, webbox, address, dtype, fix, _unit_id(webbox, unit)
    )


async def write_guarded_setpoint(
    webbox: dict[str, Any],
    param: str,
    value: float,
    confirm: bool,
    unit: int | None,
    grid_guard_code: str,
) -> dict[str, Any]:
    return await asyncio.to_thread(
        _write_guarded, webbox, param, value, confirm, _unit_id(webbox, unit), grid_guard_code
    )


async def write_raw_register(
    webbox: dict[str, Any],
    address: int,
    words: list[int],
    ack: str,
    confirm: bool,
    unit: int | None,
    raw_write_ack: str,
) -> dict[str, Any]:
    return await asyncio.to_thread(
        _write_raw, webbox, address, words, ack, confirm, _unit_id(webbox, unit), raw_write_ack
    )


__all__ = [
    "decode_words",
    "live_register_catalog",
    "read_generic_register",
    "read_live_dashboard",
    "write_guarded_setpoint",
    "write_raw_register",
    "writable_catalog",
]

from .live_registers import live_register_catalog  # noqa: E402  F401
