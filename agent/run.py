#!/usr/bin/env python3
"""Runner BangSayur: hubungkan agen ke Switch, dengarkan room, balas warga.

Arsitektur (ditemukan lewat probe, BUKAN dari dok):
  1. Buka SSE stream DULU — ops ditolak 409 kalau koneksi belum terbuka.
  2. Heartbeat tiap 5 dtk (server minta 10 dtk; 5 dtk aman dari TTL).
  3. create_room/connect_to_room — post_message TIDAK punya room_id,
     pesannya masuk ke room yang di-claim koneksi ini.
  4. Event message: data.payload.{body,sender_name,thread_id}.
     `addressed` diabaikan — addressing policy agen sudah dibuka (anyone)
     via Gateway API, dan runner menyaring sendiri berdasarkan mention.

Pemakaian:
  python3 run.py            # pakai .switch-agent.json + .room.json
  SWITCH_ROOM_ID=... python3 run.py
"""
import json
import os
import queue
import re
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# JANGAN unset proxy env di sini: panggilan Baseten HARUS lewat proxy egress
# VM (direct TCP diblokir; surrogate hsurr:* hanya diganti Sentinel di
# jalur proxy). Tanpa proxy -> Baseten terima token hsurr mentah -> 401,
# dan konek langsung menggantung. NO_PROXY bracket IPv6 hanya merusak httpx,
# bukan urllib yang dipakai agent.py/switch_client.py.
from agent import run_turn  # noqa: E402
from switch_client import SwitchClient  # noqa: E402

BASE = os.environ.get("SWITCH_BASE_URL", "http://127.0.0.1:8000")
ROOM_FILE = os.path.expanduser("~/workspace/bangsayur/.room.json")
CREDS_FILE = os.path.expanduser("~/workspace/bangsayur/.switch-agent.json")
MENTION_RE = re.compile(r"@bangsayur\b", re.IGNORECASE)


def resolve_room_id(client):
    """Pakai SWITCH_ROOM_ID / .room.json, atau buat room baru (bridged default)."""
    room_id = os.environ.get("SWITCH_ROOM_ID")
    if not room_id and os.path.exists(ROOM_FILE):
        room_id = json.load(open(ROOM_FILE)).get("room_id")
    if room_id:
        print(f"[run] pakai room {room_id}", flush=True)
        return room_id
    res = client.op("create_room", {
        "name": "Warung Sayur - Komplek Melati",
        "description": "Grup warga komplek pesan sayur ke Bang Sayur.",
        "agent_names": ["bangsayur"],
        "user_names": ["busari", "pakbudi", "buratna"],
        "channel_type": "channel_public",
        "instructions": "Room demo BangSayur: warga pesan sayur, agen Bang Sayur mencatat dan menjawab.",
    })
    room_id = res["result"]["id"]
    json.dump({"room_id": room_id}, open(ROOM_FILE, "w"))
    print(f"[run] room baru {room_id}", flush=True)
    return room_id


def read_history(client, room_id, limit=20):
    """Ambil riwayat room untuk konteks percakapan agen."""
    try:
        res = client.op("read_context", {"room_id": room_id, "limit": limit})
    except Exception as e:
        print(f"[run] read_context gagal: {e}", flush=True)
        return []
    data = res.get("result", res) if isinstance(res, dict) else res
    msgs = data.get("messages", []) if isinstance(data, dict) else data
    out = []
    for m in msgs if isinstance(msgs, list) else []:
        body = m.get("body") or m.get("text") or ""
        sender = m.get("sender_name") or m.get("sender") or ""
        if body:
            out.append({"role": "user" if sender != "bangsayur" else "assistant",
                        "content": f"{sender}: {body}" if sender else body})
    return out


def main():
    creds = json.load(open(CREDS_FILE))
    client = SwitchClient(BASE, creds["id"], creds["api_key"])
    events: queue.Queue = queue.Queue()

    def reader():
        try:
            for ev in client.events():
                events.put(ev)
        except Exception as e:
            events.put({"type": "reader_error", "error": str(e)})

    threading.Thread(target=reader, daemon=True).start()

    # tunggu connection_state (koneksi terbuka -> ops diizinkan)
    deadline = time.time() + 15
    opened = False
    while time.time() < deadline:
        try:
            ev = events.get(timeout=1)
        except queue.Empty:
            continue
        if ev.get("type") == "connection_state":
            print("[run] stream terbuka, connection_id:",
                  ev["data"].get("connection_id"), flush=True)
            opened = True
            break
    if not opened:
        print("[run] FATAL: stream tidak terbuka dalam 15 dtk", flush=True)
        return 1

    client.start_heartbeat(interval=5.0)
    room_id = resolve_room_id(client)
    print("[run] connect_to_room:",
          json.dumps(client.op("connect_to_room", {"room_id": room_id}))[:200],
          flush=True)

    print("[run] BangSayur mendengarkan room", room_id, flush=True)
    while True:
        try:
            ev = events.get(timeout=30)
        except queue.Empty:
            continue
        if ev.get("type") == "reader_error":
            print("[run] reader mati:", ev.get("error"), "- reconnect...",
                  flush=True)
            threading.Thread(target=reader, daemon=True).start()
            time.sleep(2)
            continue
        if ev.get("type") != "message":
            continue
        data = ev.get("data", {})
        payload = data.get("payload", data)
        body = (payload.get("body") or "").strip()
        sender = payload.get("sender_name") or ""
        thread_id = payload.get("thread_id")
        if not body or sender == "bangsayur":
            continue
        if not MENTION_RE.search(body):
            continue
        print(f"[run] <{sender}> {body}", flush=True)
        history = read_history(client, room_id)
        try:
            result = run_turn(f"{sender}: {body}", history=history,
                              sender=sender)
            reply = result.get("reply") or "Maaf, saya tidak mengerti."
        except Exception as e:
            print(f"[run] run_turn gagal: {e}", flush=True)
            reply = "Waduh, saya lagi error bentar. Coba ulangi pesannya ya."
        print(f"[run] > {reply}", flush=True)
        try:
            args = {"body": reply}
            if thread_id:
                args["thread_id"] = thread_id
            client.op("post_message", args)
        except Exception as e:
            print(f"[run] post_message gagal: {e}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
