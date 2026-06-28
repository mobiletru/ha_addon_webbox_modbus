"""RPC meta key ↔ Modbus register mapping for read comparison and dual-write."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CrosswalkEntry:
    label: str
    rpc_key: str
    modbus_name: str
    address: int
    writable: bool = False
    unit: str = ""
    rpc_aliases: tuple[str, ...] = ()


CROSSWALK: tuple[CrosswalkEntry, ...] = (
    CrosswalkEntry("Max charge current", "BatChrg.ChrgCurMax", "BatChrgCurMax", 40045, True, "A", ("BatChrgCurMax",)),
    CrosswalkEntry("Max discharge current", "BatDsch.DschCurMax", "BatDiChgCurMax", 40083, True, "A", ("BatDiChgCurMax",)),
    CrosswalkEntry("Float voltage", "BatChrg.FloatV", "ChrgVtgFlo", 40091, True, "V"),
    CrosswalkEntry("Boost voltage", "BatChrg.BoostV", "ChrgVtgBoost", 40085, True, "V"),
    CrosswalkEntry("Equalization voltage", "BatChrg.EquV", "ChrgVtgEqu", 40089, True, "V"),
    CrosswalkEntry("Grid frequency min", "Grid.FrqMin", "GdFrqMin", 40101, True, "Hz"),
    CrosswalkEntry("Grid frequency max", "Grid.FrqMax", "GdFrqMax", 40103, True, "Hz"),
    CrosswalkEntry("Grid voltage min", "Grid.VMin", "GdVtgMin", 40093, True, "V"),
    CrosswalkEntry("Grid voltage max", "Grid.VMax", "GdVtgMax", 40095, True, "V"),
    CrosswalkEntry("Nominal grid voltage", "Grid.VNom", "GdVtgNom", 40133, True, "V"),
    CrosswalkEntry("Nominal grid frequency", "Grid.FrqNom", "GdFrqNom", 40135, True, "Hz"),
    CrosswalkEntry("Manual start/stop", "Operation.ManStr", "ManStr", 40009, True, ""),
    CrosswalkEntry("Self-consumption SOC min", "SlfCsmp.SOCMin", "SlfCsmpSOCMin", 40073, True, "%"),
    CrosswalkEntry("Battery SOC", "BatSOC", "BatSoc", 30845, False, "%", ("Bat.Soc", "BatSoc")),
    CrosswalkEntry("Battery voltage", "BatVtg", "BatVtg", 30851, False, "V", ("Bat.Vtg",)),
    CrosswalkEntry("Battery current", "BatCur", "TotBatCur", 30843, False, "A", ("TotBatCur",)),
    CrosswalkEntry("Inverter power", "Pac", "InvPwrAt", 30777, False, "W", ("TotInvPwrAt",)),
    CrosswalkEntry("Grid import power", "GriPwr", "GdCsmpPwrAt", 30865, False, "W"),
    CrosswalkEntry("Grid export power", "GriFeed", "GdFeedPwrAt", 30867, False, "W"),
    CrosswalkEntry("PV power", "Ppv", "TotPvPwr", 30869, False, "W", ("TotPvPwr",)),
)


def crosswalk_catalog() -> list[dict[str, Any]]:
    return [asdict(e) for e in CROSSWALK]


def find_by_rpc_key(param_id: str) -> CrosswalkEntry | None:
    for entry in CROSSWALK:
        if param_id == entry.rpc_key or param_id in entry.rpc_aliases:
            return entry
    return None


def find_by_modbus_name(name: str) -> CrosswalkEntry | None:
    for entry in CROSSWALK:
        if entry.modbus_name == name:
            return entry
    return None
