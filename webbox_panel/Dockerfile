ARG BUILD_FROM
FROM $BUILD_FROM
RUN apk add --no-cache python3 py3-pip
COPY webbox_panel /usr/lib/webbox-panel/webbox_panel
COPY pyproject.toml /usr/lib/webbox-panel/
RUN pip3 install --no-cache-dir --break-system-packages /usr/lib/webbox-panel gunicorn
COPY run.sh /
RUN chmod a+x /run.sh
CMD [ "/run.sh" ]
