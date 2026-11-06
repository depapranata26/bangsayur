#!/usr/bin/env python3
"""Buka addressing policy agen BangSayur untuk semua warga.

Default Switch: agen hanya menerima instruksi dari owner (owner_only) —
warga yang mention @bangsayur akan ditolak server ("I only take instructions
from my owner..."). Script ini mengosongkan policy (PUT {"policy": null})
sehingga siapa pun di room bisa menyapa agen. Harus dijalankan sebagai
gateway admin — agen tidak bisa mengubah setting sendiri (403).

Password admin dibaca dari $SWITCH_SRC/.env (tidak dicetak).
SWITCH_SRC default-nya ../switch-src relatif terhadap repo ini.
"""
import json
import os
import sys

import httpx

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BANGSAYUR_HOME = os.environ.get("BANGSAYUR_HOME") or REPO_ROOT
SWITCH_SRC = os.environ.get("SWITCH_SRC") or os.path.join(
    REPO_ROOT, "..", "switch-src")


def getv(key, path=None):
    path = path or os.path.join(SWITCH_SRC, ".env")
    for line in open(path):
        if line.startswith(key + "="):
            return line.strip().split("=", 1)[1]
    return None


def main():
    creds_path = os.environ.get("SWITCH_CREDS_FILE") or os.path.join(
        BANGSAYUR_HOME, ".switch-agent.json")
    creds = json.load(open(creds_path))
    gw = httpx.Client(base_url="http://127.0.0.1:8000", timeout=10, trust_env=False)
    r = gw.post("/gateway/auth/login", json={
        "email": getv("GATEWAY_ADMIN_EMAIL"),
        "password": getv("GATEWAY_ADMIN_PASSWORD"),
    })
    r.raise_for_status()
    gw.headers["Cookie"] = f"switch_auth={r.cookies.get('switch_auth')}"
    r = gw.put(f"/gateway/agents/{creds['id']}/addressing-policy",
               json={"policy": None})
    print("addressing-policy:", r.status_code)
    r.raise_for_status()
    print("OK — agen BangSayur sekarang terbuka untuk semua warga di room.")


if __name__ == "__main__":
    sys.exit(main())
