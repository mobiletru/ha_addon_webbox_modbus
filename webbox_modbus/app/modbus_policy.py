"""Central Modbus write policy — single gate for all write paths."""

from __future__ import annotations

from functools import lru_cache

from .panel_writable import GRID_GUARD_REG, WRITABLE
from .profile_loader import RegisterDef, get_registers

GUARDED_PANEL_ADDRESSES: frozenset[int] = frozenset(r.address for r in WRITABLE.values())


@lru_cache(maxsize=1)
def profile_writable_addresses() -> frozenset[int]:
    return frozenset(r.address for r in get_registers().values() if r.write)


def get_register(name: str) -> RegisterDef:
    reg = get_registers().get(name)
    if reg is None:
        raise ValueError(f"Unknown register {name!r}")
    return reg


def assert_installer_password(webbox: dict) -> None:
    if not webbox.get("installer_password"):
        raise ValueError(
            "Installer password required for Modbus writes. "
            "Add it on this WebBox (or in add-on Configuration)."
        )


def assert_modbus_enabled(webbox: dict) -> None:
    if not webbox.get("modbus_enabled", True):
        raise ValueError("Modbus is disabled for this WebBox")


def assert_profile_register_write(name: str) -> RegisterDef:
    """Direct profile-table writes are disabled; use Guarded write or RPC."""
    reg = get_register(name)
    if not reg.write:
        raise ValueError(f"Register {name!r} is read-only")
    raise ValueError(
        f"Direct writes to {name!r} (@{reg.address}) are disabled. "
        "Use Guarded setpoint write for power/SOC setpoints, or RPC Parameters for device settings."
    )


def assert_raw_write_address(address: int) -> None:
    if address == GRID_GUARD_REG:
        raise ValueError(f"address {address} is the Grid Guard register — do not raw-write it")
    if address in GUARDED_PANEL_ADDRESSES:
        raise ValueError(
            f"address {address} is a guarded setpoint — use Guarded setpoint write, not raw"
        )
    if address in profile_writable_addresses():
        raise ValueError(
            f"address {address} is a profile setting register — raw write refused "
            "(use Guarded setpoint write or RPC parameters)"
        )


def is_guarded_panel_address(address: int) -> bool:
    return address in GUARDED_PANEL_ADDRESSES
