#!/usr/bin/env bash
set -uo pipefail

LOG_PREFIX="[start-container]"
log() { echo "${LOG_PREFIX} $(date -u +%Y-%m-%dT%H:%M:%SZ) $*"; }
die() { log "FATAL: $*"; exit 1; }

# PASO 1 — Proxy primero
log "PASO 1: Arrancando proxy en puerto 7860..."
python3 /app.py &
PROXY_PID=$!
sleep 2
kill -0 "${PROXY_PID}" 2>/dev/null || die "Proxy murió al arrancar."
log "Proxy activo en :7860 ✓"

# PASO 2 — Asegurar permisos
log "PASO 2: Verificando permisos..."
mkdir -p /data/gitea/conf \
         /data/gitea/data \
         /data/gitea/log \
         /data/gitea/repositories \
         /data/gitea/indexers \
         /data/ssh
chown -R git:git /data
chmod -R 755 /data
log "Permisos OK ✓"

# PASO 3 — Arrancar Gitea
log "PASO 3: Arrancando Gitea como usuario git..."
su git -c "gitea web --config /data/gitea/conf/app.ini" &
GITEA_PID=$!
log "Gitea lanzado con PID ${GITEA_PID}"

# PASO 4 — Health check
log "PASO 4: Esperando Gitea en :3000..."
attempt=0
while true; do
    curl -sSf --max-time 3 http://localhost:3000 >/dev/null 2>&1 && break
    attempt=$(( attempt + 1 ))
    [ "${attempt}" -ge 60 ] && { log "Gitea no respondió en 120s. Continuando."; break; }
    (( attempt % 10 == 0 )) && log "Esperando Gitea... ${attempt}/60"
    sleep 2
done
log "✓ Gitea listo"

# PASO 5 — Mantener container vivo
log "PASO 5: Container vivo via proxy PID ${PROXY_PID}"
wait "${PROXY_PID}"
exit $?