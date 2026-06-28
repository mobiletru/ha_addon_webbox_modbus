#!/usr/bin/with-contenv bashio
set -e
export WEBBOX_HOST="$(bashio::config 'webbox_host')"
export WEBBOX_PORT="$(bashio::config 'webbox_port')"
export WEBBOX_UNIT="$(bashio::config 'webbox_unit')"
export WEBBOX_TIMEOUT="$(bashio::config 'webbox_timeout')"
export RAW_WRITE_ACK="$(bashio::config 'raw_write_ack')"
export GRID_GUARD_CODE="$(bashio::config 'grid_guard_code')"
export PANEL_PORT=8100
bashio::log.info "WebBox Modbus Panel -> ${WEBBOX_HOST}:${WEBBOX_PORT} unit ${WEBBOX_UNIT}"
if [ -n "$RAW_WRITE_ACK" ]; then
  bashio::log.warning "Raw register write is ENABLED (ack token set)."
else
  bashio::log.info "Raw register write disabled (no ack token)."
fi
cd /usr/lib/webbox-panel
exec gunicorn -b 0.0.0.0:8100 -w 1 --timeout 30 webbox_panel.app:app
