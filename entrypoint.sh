#!/bin/sh

[ "$EXEC_TOOL" ] || EXEC_TOOL=gosu
[ "$FLATNOTES_HOST" ] || FLATNOTES_HOST=0.0.0.0
[ "$FLATNOTES_PORT" ] || FLATNOTES_PORT=2908
[ "$FLATNOTES_AUTH_TYPE" ] || FLATNOTES_AUTH_TYPE=password
[ "$FLATNOTES_USERNAME" ] || FLATNOTES_USERNAME=admin
[ "$FLATNOTES_PASSWORD" ] || FLATNOTES_PASSWORD=slingshot123
[ "$FLATNOTES_SECRET_KEY" ] || FLATNOTES_SECRET_KEY=slingshot-dev-secret-key-change-me

export FLATNOTES_AUTH_TYPE
export FLATNOTES_USERNAME
export FLATNOTES_PASSWORD
export FLATNOTES_SECRET_KEY

set -e

echo "\
======================================
======== Welcome to Slingshot ========
======================================
Login: ${FLATNOTES_USERNAME}
Password: ${FLATNOTES_PASSWORD}
──────────────────────────────────────
"

slingshot_command="python -m \
                  uvicorn \
                  main:app \
                  --app-dir server \
                  --host ${FLATNOTES_HOST} \
                  --port ${FLATNOTES_PORT} \
                  --proxy-headers \
                  --forwarded-allow-ips '*'"

if [ `id -u` -eq 0 ] && [ `id -g` -eq 0 ]; then
    echo Setting file permissions...
    chown -R ${PUID}:${PGID} ${FLATNOTES_PATH}
    echo Starting Slingshot as user ${PUID}...
    exec ${EXEC_TOOL} ${PUID}:${PGID} ${slingshot_command}
else
    echo "A user was set by docker, skipping file permission changes."
    echo Starting Slingshot as user $(id -u)...
    exec ${slingshot_command}
fi
