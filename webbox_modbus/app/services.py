"""Shared RPC + Modbus orchestration helpers."""

from __future__ import annotations

import asyncio
import math
from typing import Any

from .crosswalk import CROSSWALK, CrosswalkEntry, find_by_rpc_key
from .modbus_client import SMAModbusClient
from .parameters import enrich_parameters
from .profile_loader import get_registers, register_catalog
from .webbox.client import WebBoxClient, WebBoxCredentials, WebBoxError


def modbus_client_for(webbox: dict[str, Any]) -> SMAModbusClient:
    return SMAModbusClient(
        webbox["host"],
        port=int(webbox.get("modbus_port") or 502),
        unit_id=int(webbox.get("modbus_unit_id") or 3),
    )


def webbox_client_for(webbox: dict[str, Any]) -> WebBoxClient:
    creds = WebBoxCredentials(
        user_password=webbox.get("password") or None,
        installer_password=webbox.get("installer_password") or None,
    )
    return WebBoxClient(webbox["host"], credentials=creds)


def _rpc_lookup(parameters: list[dict[str, Any]], entry: CrosswalkEntry) -> Any:
    keys = (entry.rpc_key, *entry.rpc_aliases)
    for param in parameters:
        for key in keys:
            if param.get("key") == key or param.get("name") == key:
                return param.get("value")
    return None


def _values_match(a: Any, b: Any, *, tolerance: float = 0.05) -> bool:
    if a is None or b is None:
        return False
    try:
        fa, fb = float(a), float(b)
        if math.isfinite(fa) and math.isfinite(fb):
            if fa == fb:
                return True
            return abs(fa - fb) <= tolerance
    except (TypeError, ValueError):
        pass
    return str(a) == str(b)


async def read_modbus_registers(webbox: dict[str, Any], names: list[str]) -> dict[str, Any]:
    if not webbox.get("modbus_enabled", True):
        return {"online": False, "error": "Modbus disabled for this WebBox", "registers": {}}

    client = modbus_client_for(webbox)

    def _read() -> dict[str, Any]:
        try:
            values = client.read_many(names)
            return {"online": True, "registers": values}
        except Exception as exc:
            return {"online": False, "error": str(exc), "registers": {}}
        finally:
            client.close()

    return await asyncio.to_thread(_read)


async def write_modbus_register(webbox: dict[str, Any], name: str, value: Any) -> None:
    client = modbus_client_for(webbox)

    def _write() -> None:
        try:
            client.write_register(name, value)
        finally:
            client.close()

    await asyncio.to_thread(_write)


async def read_rpc_parameter(
    webbox: dict[str, Any], device_key: str, rpc_key: str
) -> Any:
    async with webbox_client_for(webbox) as client:
        rows = await client.get_parameters(device_key, [rpc_key])
    enriched = enrich_parameters(rows)
    return enriched[0].get("value") if enriched else None


async def write_rpc_parameter(
    webbox: dict[str, Any], device_key: str, rpc_key: str, value: Any
) -> None:
    if not webbox.get("installer_password"):
        raise ValueError("Installer password is required for RPC writes.")
    async with webbox_client_for(webbox) as client:
        await client.set_parameter(device_key, rpc_key, value)


async def dual_write_parameter(
    webbox: dict[str, Any],
    device_key: str,
    param_id: str,
    value: Any,
    via: str,
) -> dict[str, Any]:
    entry = find_by_rpc_key(param_id)
    if not entry:
        raise ValueError(f"Unknown crosswalk parameter {param_id!r}")

    written_via: list[str] = []
    if via in ("rpc", "both"):
        await write_rpc_parameter(webbox, device_key, entry.rpc_key, value)
        written_via.append("rpc")
    if via in ("modbus", "both"):
        from .modbus_policy import assert_installer_password, get_register, is_guarded_panel_address

        assert_installer_password(webbox)
        reg = get_register(entry.modbus_name)
        if is_guarded_panel_address(reg.address):
            raise ValueError(
                f"{entry.modbus_name} (@{reg.address}) must be written via Guarded setpoint write, "
                "not dual-write or profile table."
            )
        await write_modbus_register(webbox, entry.modbus_name, value)
        written_via.append("modbus")

    rpc_value = await read_rpc_parameter(webbox, device_key, entry.rpc_key)
    modbus_result = await read_modbus_registers(webbox, [entry.modbus_name])
    modbus_value = modbus_result.get("registers", {}).get(entry.modbus_name)

    return {
        "param": entry.rpc_key,
        "label": entry.label,
        "written_via": written_via,
        "rpc_value": rpc_value,
        "modbus_value": modbus_value,
        "unit": entry.unit,
        "match": _values_match(rpc_value, modbus_value),
        "warning": None
        if _values_match(rpc_value, modbus_value)
        else "RPC and Modbus read-back differ after write",
    }


async def build_snapshot(
    webbox: dict[str, Any],
    device_key: str | None = None,
) -> dict[str, Any]:
    rpc_block: dict[str, Any] = {"online": False, "overview": {}, "process": [], "parameters": []}
    modbus_block: dict[str, Any] = {"online": False, "registers": {}}

    modbus_names = sorted({e.modbus_name for e in CROSSWALK})
    registers = get_registers()
    modbus_names = [n for n in modbus_names if n in registers]

    async with webbox_client_for(webbox) as client:
        try:
            overview = await client.plant_overview()
            devices = await client.list_devices()
            rpc_block["online"] = True
            rpc_block["overview"] = overview
            rpc_block["devices"] = devices

            if not device_key:
                device_key = _find_sunny_island_key(devices)

            if device_key:
                rpc_block["process"] = await client.process_data(device_key)
                try:
                    raw_params = await client.get_parameters(device_key)
                    rpc_block["parameters"] = enrich_parameters(raw_params)
                except WebBoxError:
                    rpc_block["parameters"] = []
        except WebBoxError as exc:
            rpc_block["error"] = str(exc)

    modbus_block = await read_modbus_registers(webbox, modbus_names)

    comparison = []
    params = rpc_block.get("parameters") or []
    modbus_values = modbus_block.get("registers") or {}
    for entry in CROSSWALK:
        rpc_value = _rpc_lookup(params, entry)
        if rpc_value is None and rpc_block.get("process"):
            rpc_value = _process_lookup(rpc_block["process"], entry)
        modbus_value = modbus_values.get(entry.modbus_name)
        comparison.append(
            {
                "label": entry.label,
                "rpc_key": entry.rpc_key,
                "modbus_name": entry.modbus_name,
                "address": entry.address,
                "writable": entry.writable,
                "unit": entry.unit,
                "rpc_value": rpc_value,
                "modbus_value": modbus_value,
                "match": _values_match(rpc_value, modbus_value),
            }
        )

    return {
        "rpc": rpc_block,
        "modbus": modbus_block,
        "comparison": comparison,
        "device_key": device_key,
    }


def _find_sunny_island_key(devices: list[dict[str, Any]]) -> str | None:
    for dev in devices:
        key = (dev.get("key") or "").upper()
        name = (dev.get("name") or "").upper()
        if "SI604" in key or "SUNNY ISLAND" in name or key.startswith("SI"):
            return dev.get("key")
        for child in dev.get("children") or []:
            found = _find_sunny_island_key([child])
            if found:
                return found
    return devices[0].get("key") if devices else None


def _process_lookup(process: list[dict[str, Any]], entry: CrosswalkEntry) -> Any:
    keys = (entry.rpc_key, *entry.rpc_aliases, entry.modbus_name)
    for row in process:
        name = row.get("name") or ""
        if name in keys:
            return row.get("value")
    return None


def modbus_register_rows(webbox: dict[str, Any]) -> list[dict[str, Any]]:
    catalog = register_catalog()
    return catalog
