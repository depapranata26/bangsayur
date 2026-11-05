#!/usr/bin/env python3
"""Probe: buka stream, buat room Mattermost, kirim pesan sbg warga, lihat event.

Dipakai sekali untuk memvalidasi bentuk event sebelum finalisasi run.py.
"""
import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.expanduser("~/workspace/bangsayur/agent"))
os.environ.pop("http_proxy", None); os.environ.pop("https_proxy", None)
os.environ.pop("HTTP_PROXY", None); os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("ALL_PROXY", None); os.environ.pop("all_proxy", None)

from switch_client import SwitchClient  # noqa: E402

BASE = os.environ.get("SWITCH_BASE_URL", "http://127.0.0.1:8000")
CREDS = json.load(open(os.path.expanduser("~/workspace/bangsayur/.switch-agent.json")))
c = SwitchClient(BASE, CREDS["id"], CREDS["api_key"])

events = []
stop = threading.Event()


def reader():
    try:
        for ev in c.events():
            events.append(ev)
            print("EV:", json.dumps(ev, ensure_ascii=False)[:800], flush=True)
            if stop.is_set():
                break
    except Exception as e:
        print("reader error:", e, flush=True)


t = threading.Thread(target=reader, daemon=True)
t.start()
time.sleep(3)

room_id = json.load(open(os.path.expanduser("~/workspace/bangsayur/.room.json")))["room_id"]
print("REUSE ROOM:", room_id, flush=True)
print("connect:", json.dumps(c.op("connect_to_room", {"room_id": room_id}), ensure_ascii=False)[:400], flush=True)

# kirim pesan sebagai warga via API Mattermost langsung ke channel
import httpx  # noqa: E402
mm = httpx.Client(base_url="http://localhost:8065", timeout=10, trust_env=False)
r = mm.post("/api/v4/users/login", json={"login_id": "busari", "password": "warga-pw"})
mm.headers["Authorization"] = f"Bearer {r.headers['token']}"
# cari channel room (nama slug dari nama room)
team = mm.get("/api/v4/teams/name/komplek-melati").json()
chans = mm.get(f"/api/v4/teams/{team['id']}/channels").json()
print("CHANNELS:", [(ch["name"], ch["display_name"], ch["id"][:8]) for ch in chans], flush=True)
target = next((ch for ch in chans if "sayur" in ch["name"].lower() or "melati" in ch["name"].lower()), None)
if target:
    p = mm.post("/api/v4/posts", json={"channel_id": target["id"], "message": "@bangsayur halo bang, saya mau pesan 2 ikat kangkung sama 1 kg cabai merah"})
    print("POST as busari:", p.status_code, p.text[:200], flush=True)

time.sleep(6)
stop.set()
c.stop()
print("TOTAL EVENTS:", len(events))
