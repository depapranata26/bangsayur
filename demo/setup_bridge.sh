#!/usr/bin/env bash
# Setup bridge Mattermost <-> Switch (adaptasi deploy/shared_resources/setup.py).
# Baca secret dari ~/workspace/switch-src/.env — jangan print isinya.
set -e
# VM ini punya NO_PROXY berisi entri IPv6 bracket yang httpx tak bisa parse —
# unset semua proxy env (semua target di localhost, tak butuh proxy).
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy NO_PROXY no_proxy
export NO_PROXY=localhost,127.0.0.1
export no_proxy=localhost,127.0.0.1
SWITCH_ENV="$HOME/workspace/switch-src/.env"
getv() { grep -E "^$1=" "$SWITCH_ENV" | head -1 | cut -d= -f2-; }

export SWITCH_URL=http://127.0.0.1:8000
export GATEWAY_ADMIN_EMAIL="$(getv GATEWAY_ADMIN_EMAIL)"
export GATEWAY_ADMIN_PASSWORD="$(getv GATEWAY_ADMIN_PASSWORD)"
export MATTERMOST_URL=http://localhost:8065
export MATTERMOST_URL_FOR_SWITCH=http://localhost:8065
export MATTERMOST_CALLBACK_BASE_URL=http://localhost:8081
export MATTERMOST_ADMIN_USER=pemilik
export MATTERMOST_ADMIN_PASSWORD="pemilik-pw"
export MATTERMOST_TEAM_NAME=komplek-melati
export MATTERMOST_USER=warga
export MATTERMOST_USER_PASSWORD="warga-pw"

"$HOME/workspace/bangsayur/demo/venv/bin/python" "$HOME/workspace/switch-src/deploy/shared_resources/setup.py"
