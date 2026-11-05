#!/usr/bin/env bash
# Start switch-core (repo ~/workspace/switch-src) dengan .env ter-load.
# .env TIDAK di-load otomatis oleh `uv run` — justfile memakai dotenv-load,
# tapi `just` tidak terinstal di VM ini, jadi source manual.
# Proxy env VM berisi NO_PROXY IPv6 bracket yang httpx tak bisa parse -> unset.
set -e
cd "$HOME/workspace/switch-src"
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy NO_PROXY no_proxy
export NO_PROXY=localhost,127.0.0.1
export no_proxy=localhost,127.0.0.1
export GATEWAY_COOKIE_SECURE=false
set -a
# shellcheck disable=SC1091
. ./.env
set +a
exec /tmp/uv-x86_64-unknown-linux-gnu/uv run --project core python -m switch_core.main
