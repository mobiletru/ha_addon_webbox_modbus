"""Sunny Boy live read map (FC03 holding registers).

Extracted from SMA MODBUS-HTML_SB30-77-1SP-US-40_V11 / modbuslist_en.html
Devices: SB3.0–SB7.7-1SP-US-40 (firmware 2.04.97.R+).
WebBox gateway: Modbus TCP port 502, Sunny Boy unit id typically 3 (not 23).

Use Operation.Health @ 30201 as online/status probe (no battery SOC on PV inverters).
"""

from __future__ import annotations

from dataclasses import asdict

from .live_registers import LiveReg, decode_live_reg

# Recommended status probe for SB (TAGLIST: 35=Fault, 303=Off, 307=Ok, 455=Warning)
STATUS_PROBE_ADDRESS = 30201

DEFAULT_MAP: list[LiveReg] = [
    LiveReg("health", 30201, 2, False, 1, "", "Condition (Op.Health)", None),
    LiveReg("ac_power_w", 30775, 2, True, 1, "W", "AC Power (Pac)", "power"),
    LiveReg("grid_feed_w", 30867, 2, True, 1, "W", "Grid Feed-in (TotWOut)", "power"),
    LiveReg("grid_draw_w", 30865, 2, True, 1, "W", "Grid Draw (TotWIn)", "power"),
    LiveReg("frequency_hz", 30803, 2, False, 0.01, "Hz", "Grid Frequency", "frequency"),
    LiveReg("grid_voltage_l1_v", 30783, 2, False, 0.01, "V", "Grid Voltage L1", "voltage"),
    LiveReg("grid_voltage_l2_v", 30785, 2, False, 0.01, "V", "Grid Voltage L2", "voltage"),
    LiveReg("grid_voltage_l3_v", 30787, 2, False, 0.01, "V", "Grid Voltage L3", "voltage"),
    LiveReg("dc_power_a_w", 30773, 2, True, 1, "W", "DC Power Input A", "power"),
    LiveReg("dc_voltage_a_v", 30771, 2, True, 0.01, "V", "DC Voltage Input A", "voltage"),
    LiveReg("dc_current_a_a", 30769, 2, True, 0.001, "A", "DC Current Input A", "current"),
    LiveReg("dc_power_b_w", 30961, 2, True, 1, "W", "DC Power Input B", "power"),
    LiveReg("total_yield_kwh", 30531, 2, False, 1, "kWh", "Total Yield", "energy"),
    LiveReg("total_yield_wh", 30529, 2, False, 1, "Wh", "Total Yield (Wh)", "energy"),
    LiveReg("grid_feed_energy_wh", 30583, 2, False, 1, "Wh", "Grid Feed-in Counter", "energy"),
    LiveReg("cabinet_temp_c", 30953, 2, True, 0.1, "°C", "Internal Temperature", "temperature"),
]


def live_register_catalog() -> list[dict]:
    rows = [asdict(r) for r in DEFAULT_MAP]
    for row in rows:
        row["sma_name"] = _SMA_NAMES.get(row["name"], "")
    return rows


def catalog_meta() -> dict:
    return {
        "profile": "SB30-77-1SP-US-40_V11",
        "devices": [
            "SB3.0-1SP-US-40",
            "SB3.8-1SP-US-40",
            "SB5.0-1SP-US-40",
            "SB6.0-1SP-US-40",
            "SB7.0-1SP-US-40",
            "SB7.7-1SP-US-40",
        ],
        "min_firmware": "2.04.97.R",
        "status_probe_address": STATUS_PROBE_ADDRESS,
        "register_count": len(DEFAULT_MAP),
        "default_unit_id": 3,
        "source": "modbuslist_en.html",
    }


_SMA_NAMES: dict[str, str] = {
    "health": "Operation.Health",
    "ac_power_w": "GridMs.TotW",
    "grid_feed_w": "Metering.GridMs.TotWOut",
    "grid_draw_w": "Metering.GridMs.TotWIn",
    "frequency_hz": "GridMs.Hz",
    "grid_voltage_l1_v": "GridMs.PhV.phsA",
    "grid_voltage_l2_v": "GridMs.PhV.phsB",
    "grid_voltage_l3_v": "GridMs.PhV.phsC",
    "dc_power_a_w": "DcMs.Watt",
    "dc_voltage_a_v": "DcMs.Vol",
    "dc_current_a_a": "DcMs.Amp",
    "dc_power_b_w": "DcMs.Watt",
    "total_yield_kwh": "Metering.TotWhOut",
    "total_yield_wh": "Metering.TotWhOut",
    "grid_feed_energy_wh": "Metering.GridMs.TotWhOut",
    "cabinet_temp_c": "Coolsys.Cab.TmpVal",
}


__all__ = [
    "DEFAULT_MAP",
    "STATUS_PROBE_ADDRESS",
    "catalog_meta",
    "decode_live_reg",
    "live_register_catalog",
]
