#!/usr/bin/env python3
"""Kirim skenario demo ke channel Mattermost sebagai warga simulasi.

Dipakai untuk tes end-to-end live: tiap pesan dikirim sebagai user
Mattermost yang berbeda, lalu tunggu agen membalas sebelum lanjut.
"""
import sys
import time

import httpx

MM = "http://localhost:8065"
CHANNEL_SUBSTR = "sayur"  # pilih channel sayur terbaru (room baru = slug baru)

SCENARIO = [
    ("busari", "@bangsayur halo bang, saya mau pesan 2 ikat kangkung sama 1 kg cabai merah"),
    ("pakbudi", "@bangsayur bang, saya mau 1 kg telur ayam sama 2 papan tempe"),
    ("buratna", "@bangsayur total pesanan hari ini berapa bang?"),
    ("pakbudi", "@bangsayur rute hari ini gimana?"),
    ("buratna", "@bangsayur siapa aja yang belum bayar?"),
    # CATATAN: jangan pakai user `pemilik` untuk bertanya — itu akun admin
    # bridge Mattermost, dan adapter Switch sengaja mengabaikan postingannya
    # (dianggap gema dari bridge itu sendiri). Omzet ditanya dari akun `warga`
    # (tukang sayurnya sendiri).
    ("warga", "@bangsayur rekap omzet hari ini dong"),
]


def login(mm, user, pw="warga-pw"):
    r = mm.post("/api/v4/users/login", json={"login_id": user, "password": pw})
    r.raise_for_status()
    return r.headers["token"]


def main():
    mm = httpx.Client(base_url=MM, timeout=10, trust_env=False)
    mm.headers["Authorization"] = f"Bearer {login(mm, 'pemilik', 'pemilik-pw')}"
    team = mm.get("/api/v4/teams/name/komplek-melati").json()
    chans = mm.get(f"/api/v4/teams/{team['id']}/channels").json()
    sayur = [c for c in chans if CHANNEL_SUBSTR in c["name"]]
    ch = max(sayur, key=lambda c: c.get("create_at", 0))
    print(f"channel: {ch['name']} ({ch['display_name']})", flush=True)
    tokens = {}
    for user, msg in SCENARIO:
        if user not in tokens:
            tokens[user] = login(mm, user, "pemilik-pw" if user == "pemilik" else "warga-pw")
        mm.headers["Authorization"] = f"Bearer {tokens[user]}"
        r = mm.post("/api/v4/posts", json={"channel_id": ch["id"], "message": msg})
        print(f"[{user}] -> {r.status_code} {msg[:60]}", flush=True)
        time.sleep(20)  # beri waktu agen mikir (model call ~5-15 dtk) + post
    print("Skenario selesai. Cek channel untuk balasan agen.")


if __name__ == "__main__":
    sys.exit(main())
