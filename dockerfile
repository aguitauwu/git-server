FROM gitea/gitea:latest

USER root

RUN apk add --no-cache python3 py3-pip curl bash && \
    pip3 install --no-cache-dir fastapi uvicorn httpx --break-system-packages

RUN id git 2>/dev/null || adduser -D -s /bin/bash -h /home/git git

RUN mkdir -p /data/gitea/conf \
             /data/gitea/data \
             /data/gitea/log \
             /data/gitea/repositories \
             /data/gitea/indexers \
             /data/ssh && \
    chown -R git:git /data && \
    chmod -R 755 /data

COPY app.ini /data/gitea/conf/app.ini
RUN chown git:git /data/gitea/conf/app.ini && chmod 644 /data/gitea/conf/app.ini

COPY app.py /app.py
COPY start-container.sh /start-container.sh
RUN chmod +x /start-container.sh

ENV GITEA_WORK_DIR=/data/gitea
ENV GITEA_CUSTOM=/data/gitea

EXPOSE 7860 300

ENTRYPOINT ["/bin/bash", "/start-container.sh"]