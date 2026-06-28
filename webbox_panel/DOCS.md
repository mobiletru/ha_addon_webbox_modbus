# WebBox Sunny Island Modbus Panel

Modbus-only panel for the Sunny Island via the WebBox gateway (port 502).

## Sections

1. **Live dashboard** — verified register map (SOC, voltage, current, temp, AC power, grid Hz, daily yield), auto-refresh every 5s.
2. **Register explorer** — read any address with U16/S16/U32/S32/U64/S64 and FIX scaling. Walk the SI parameter table and discover what your firmware exposes.
3. **Guarded setpoint write** — known RW setpoints, range-clamped, read-back verified. Use **Check** then **Write & verify**.
4. **Raw write (advanced)** — off unless `raw_write_ack` is set in add-on configuration.

## Configuration

| Option | Default | Purpose |
|--------|---------|---------|
| `webbox_host` | — | WebBox IP/hostname |
| `webbox_port` | 502 | Modbus TCP port |
| `webbox_unit` | 23 | Modbus unit ID (try 3 if 23 fails) |
| `webbox_timeout` | 5 | Connection timeout (seconds) |
| `grid_guard_code` | — | SMA Grid Guard code for protected writes |
| `raw_write_ack` | — | Token to enable raw write in the UI |

## Safety

Battery chemistry is not writable over Modbus. Clamped safety registers must use the guarded write path, not raw write.
