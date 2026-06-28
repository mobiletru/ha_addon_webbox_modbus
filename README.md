# WebBox Modbus Dashboard

Home Assistant OS add-on: Sunny WebBox **JSON-RPC** + **Modbus TCP** dashboard for Sunny Island 6048.

## Features

- Multi-WebBox management (add, scan, edit, delete)
- Plant overview and device tree via WebBox RPC
- Live process data, parameter editor, named commands
- Modbus register map from `SI6048MBP.xml`
- Dual-source snapshot and RPC/Modbus parameter writes
- Ingress panel in Home Assistant

## Install in Home Assistant

1. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
2. Add: `https://github.com/mobiletru/ha_addon_webbox_modbus`
3. Install **WebBox Modbus Dashboard**
4. Configure WebBox host, passwords, and Modbus settings (port `502`, unit ID `3`)
5. Start the add-on and open the panel

## Configuration

| Option | Description |
|--------|-------------|
| `webboxes` | Pre-seed WebBoxes (host, passwords, modbus_port, modbus_unit_id) |
| `scan_subnet` | Default /24 for subnet scan (e.g. `192.168.1`) |
| `log_level` | Logging verbosity |

## Local development

```powershell
cd modbus_dashboard
.\dev.ps1
```

Open http://127.0.0.1:8765

## License

MIT
