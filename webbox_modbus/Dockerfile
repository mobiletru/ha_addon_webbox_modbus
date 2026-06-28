ARG BUILD_FROM
ARG BUILD_ARCH=amd64
FROM ${BUILD_FROM}

ENV LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/opt/webbox \
    MODBUS_PROFILE_PATH=/opt/webbox/profiles/SI6048MBP.xml

RUN apk add --no-cache python3 py3-pip ca-certificates wget

WORKDIR /opt/webbox

COPY requirements.txt .
RUN pip3 install --break-system-packages -r requirements.txt

COPY app ./app
COPY profiles ./profiles
COPY run.sh /run.sh
RUN chmod a+x /run.sh

EXPOSE 8099

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:8099/api/health || exit 1

CMD ["/run.sh"]
