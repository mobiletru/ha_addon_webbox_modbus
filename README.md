# WebBox Modbus — Home Assistant OS Add-ons

Two add-ons for SMA Sunny WebBox / Sunny Island over Modbus TCP (port 502).

## Install in Home Assistant

1. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
2. Add: `https://github.com/mobiletru/ha_addon_webbox_modbus`
3. Install one or both add-ons below
4. Configure host, port **502**, and Modbus unit ID
5. **Rebuild** then **Start**

## Add-ons

### WebBox Modbus Dashboard (`webbox_modbus`)

Full **JSON-RPC + Modbus** dashboard: WebBox device tree, parameters, commands, all **140 SI6048MBP registers**, RPC vs Modbus compare.

- Sidebar panel: **WebBox Modbus**
- Ingress port: 8099
- Needs WebBox installer password for RPC writes

### WebBox Sunny Island Modbus Panel (`webbox_panel`)

Focused **Modbus-only** panel from the SI live register map:

- Live dashboard (SOC, V, I, temp, power, Hz)
- **Register explorer** — read any address/type
- **Guarded setpoint writes** (clamped + verified)
- Optional ack-gated raw write

- Sidebar panel: **SI Modbus**
- Ingress port: 8100
- Default unit ID **23** (change to **3** if your WebBox uses that)

## Repository structure

```
repository.yaml
webbox_modbus/     ← RPC + Modbus dashboard (FastAPI)
webbox_panel/      ← Modbus panel (Flask, register explorer)
```

## Example — Modbus Dashboard

```yaml
webboxes:
  - name: SI6048
    host: 192.168.1.42
    installer_password: "your-installer-pw"
    modbus_port: 502
    modbus_unit_id: 3
    modbus_enabled: true
```

## Example — Modbus Panel

```yaml
webbox_host: 192.168.1.42
webbox_port: 502
webbox_unit: 3
webbox_timeout: 5
```

## Local development

```powershell
# RPC + Modbus dashboard
.\dev.ps1

# Modbus panel only
cd webbox_panel
pip install -e .
$env:WEBBOX_HOST="192.168.1.42"; $env:WEBBOX_UNIT="3"; webbox-panel
```

## License

MIT
