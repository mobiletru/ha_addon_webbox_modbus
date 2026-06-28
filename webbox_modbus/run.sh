#!/usr/bin/env sh
set -e

export WEBBOX_OPTIONS_PATH=/data/options.json
export WEBBOX_DATA_DIR=/data
export WEBBOX_HOST=0.0.0.0
export WEBBOX_PORT=8099
export MODBUS_PROFILE_PATH=/opt/webbox/profiles/SI6048MBP.xml

LOG_LEVEL="$(python3 -c 'import json,os;print(json.load(open(os.environ["WEBBOX_OPTIONS_PATH"])).get("log_level","info"))' 2>/dev/null || echo info)"
export WEBBOX_LOG_LEVEL="${LOG_LEVEL}"

echo "[webbox-modbus] starting on ${WEBBOX_HOST}:${WEBBOX_PORT} (log_level=${WEBBOX_LOG_LEVEL})"

exec python3 -m uvicorn app.main:app \
    --host "${WEBBOX_HOST}" \
    --port "${WEBBOX_PORT}" \
    --log-level "${WEBBOX_LOG_LEVEL}" \
    --app-dir /opt/webbox
