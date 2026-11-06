#!/usr/bin/env bash
# Start switch-core (repo $SWITCH_SRC) dengan .env ter-load.
# SWITCH_SRC default: ../switch-src relatif terhadap repo ini.
# UV_BIN override: path ke binary uv (default: uv di PATH).
# .env TIDAK di-load otomatis oleh `uv run` — justfile memakai dotenv-load,
# tapi `just` tidak terinstal di VM ini, jadi source manual.
# Proxy env VM berisi NO_PROXY IPv6 bracket yang httpx tak bisa parse -> unset.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${BANGSAYUR_HOME:-$(cd "$SCRIPT_DIR/.." && pwd)}"
SWITCH_SRC="${SWITCH_SRC:-$(cd "$REPO_ROOT/.." && pwd)/switch-src}"
cd "$SWITCH_SRC"
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy NO_PROXY no_proxy
export NO_PROXY=localhost,127.0.0.1
export no_proxy=localhost,127.0.0.1
export GATEWAY_COOKIE_SECURE=false
set -a
# shellcheck disable=SC1091
. ./.env
set +a
exec "${UV_BIN:-uv}" run --project core python -m switch_core.main
