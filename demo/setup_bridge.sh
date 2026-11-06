#!/usr/bin/env bash
# Setup bridge Mattermost <-> Switch (adaptasi deploy/shared_resources/setup.py).
# Baca secret dari $SWITCH_SRC/.env — jangan print isinya.
# SWITCH_SRC default: ../switch-src relatif terhadap repo ini.
# BANGSAYUR_HOME default: repo root (direktori induk demo/).
set -e
# VM ini punya NO_PROXY berisi entri IPv6 bracket yang httpx tak bisa parse —
# unset semua proxy env (semua target di localhost, tak butuh proxy).
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy NO_PROXY no_proxy
export NO_PROXY=localhost,127.0.0.1
export no_proxy=localhost,127.0.0.1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${BANGSAYUR_HOME:-$(cd "$SCRIPT_DIR/.." && pwd)}"
SWITCH_SRC="${SWITCH_SRC:-$(cd "$REPO_ROOT/.." && pwd)/switch-src}"
SWITCH_ENV="$SWITCH_SRC/.env"
getv() { grep -E "^$1=" "$SWITCH_ENV" | head -1 | cut -d= -f2-; }

export SWITCH_URL=http://127.0.0.1:8000
export GATEWAY_ADMIN_EMAIL="$(getv GATEWAY_ADMIN_EMAIL)"
export GATEWAY_ADMIN_PASSWORD="$(getv GATEWAY_ADMIN_PASSWORD)"
export MATTERMOST_URL=http://localhost:8065
export MATTERMOST_URL_FOR_SWITCH=http://localhost:8065
export MATTERMOST_CALLBACK_BASE_URL=http://localhost:8081
export MATTERMOST_ADMIN_USER=pemilik
export MATTERMOST_ADMIN_PASSWORD="${MATTERMOST_ADMIN_PASSWORD:-pemilik-pw}"
export MATTERMOST_TEAM_NAME=komplek-melati
export MATTERMOST_USER=warga
export MATTERMOST_USER_PASSWORD="${MATTERMOST_USER_PASSWORD:-warga-pw}"

"$REPO_ROOT/demo/venv/bin/python" "$SWITCH_SRC/deploy/shared_resources/setup.py"
