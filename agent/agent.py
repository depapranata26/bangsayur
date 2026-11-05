#!/usr/bin/env python3
"""BangSayur agent brain: Muse Spark (Baseten) driving the vegetable-vendor tools.

Loop: room message -> model (OpenAI-style tools) -> tools on SQLite -> reply.
Key-nya TIDAK PERNAH ditulis ke file/log/repo: pakai pola Secure Vault yang
sama seperti MejaBahasa (dynamic_credentials surrogate).
"""
import json
import re
import sys
import urllib.error
import urllib.request

try:
    sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
    from dynamic_credentials import add_surrogate_to_request, read_json_response
except ImportError:
    import os

    def _get_key():
        return os.environ.get("BASENTEN_API_KEY", "")

    def add_surrogate_to_request(req, *a, **k):
        req.add_header("Authorization", f"Bearer {_get_key()}")

    def read_json_response(resp):
        return json.loads(resp.read().decode("utf-8"))

import tools as tools_mod

MODEL = "meta-models/muse-spark-open-1026"
BASE_URL = "https://inference.baseten.co/v1"

SYSTEM_PROMPT = """Kamu Bang Sayur, agen tukang sayur keliling di grup chat warga komplek.
Kamu membantu warga pesan sayur, dan membantu Bang Sayur (tukang sayurnya)
mengelola pesanan, rute, tagihan, dan omzet.

GAYA BICARA: Bahasa Indonesia sehari-hari, ramah, singkat, kayak abang sayur
beneran. Panggil warga dengan nama aslinya kalau tahu (cek cari_pelanggan —
username chat "buratna" itu Bu Ratna, "busari" itu Bu Sari, "pakbudi" itu
Pak Budi; jangan menyapa dengan username mentah). Pakai emoji secukupnya
(🥬🧅🥕💰🛵). JANGAN pakai markdown (tebal, heading, backtick) — tulis teks
polos, satu item per baris diawali "• ".

ATURAN KERAS:
1. Harga dan stok HANYA dari tools (database). JANGAN PERNAH mengarang harga,
   stok, atau nama sayur. Kalau warga menyebut sayur yang tidak ada di daftar,
   bilang tidak ada dan tawarkan yang mirip dari daftar_harga.
2. Sebelum mencatat pesanan, pastikan ada: nama pemesan, blok (A/B/C/D), dan
   item + jumlah. Cek dulu cari_pelanggan — kalau pemesan sudah dikenal,
   pakai bloknya dari database, jangan tanya lagi. Kalau ada yang kurang,
   tanya dulu — jangan menebak.
3. Setiap pesanan yang dicatat status bayarnya 'belum' sampai ada yang bilang
   sudah bayar (tandai_lunas). Jangan pernah bilang "sudah lunas" tanpa tool.
4. Jangan pernah mengarang nomor pesanan, total, atau omzet — hanya dari hasil tool.
5. Kalau stok tidak cukup, bilang sisanya berapa dan tawarkan jumlah yang tersedia
   atau sayur pengganti.
6. Jawab singkat dan padat, cocok dibaca di HP. Kalau ditanya rekap/rute/tagihan,
   tampilkan sebagai daftar, bukan paragraf panjang.
7. Kamu hanya urusan sayur dan jualan: pesanan, harga, stok, rute, tagihan,
   omzet. Kalau ditanya di luar itu, jawab sopan bahwa itu bukan urusan Bang Sayur.
"""

OPENAI_TOOLS = [
    {"type": "function", "function": {
        "name": "daftar_harga",
        "description": "Daftar semua sayur + harga + stok hari ini. Satu-satunya sumber harga.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "cari_pelanggan",
        "description": "Cari pelanggan berdasarkan nama. Dipakai SEBELUM mencatat pesanan: kalau pemesan sudah dikenal, pakai bloknya dari database dan jangan tanya blok lagi.",
        "parameters": {"type": "object", "properties": {
            "nama": {"type": "string", "description": "Nama pemesan."},
        }, "required": ["nama"]},
    }},
    {"type": "function", "function": {
        "name": "catat_pesanan",
        "description": "Catat pesanan baru warga. Harga dihitung dari database, stok dicek dan dikurangi otomatis.",
        "parameters": {"type": "object", "properties": {
            "nama": {"type": "string", "description": "Nama pemesan."},
            "blok": {"type": "string", "enum": ["A", "B", "C", "D"]},
            "items": {"type": "array", "items": {"type": "object", "properties": {
                "nama_item": {"type": "string"},
                "qty": {"type": "number"}}, "required": ["nama_item", "qty"]}},
        }, "required": ["nama", "blok", "items"]},
    }},
    {"type": "function", "function": {
        "name": "rekap_harian",
        "description": "Rekap pesanan hari ini (atau tanggal tertentu): jumlah pesanan, total per item, omzet.",
        "parameters": {"type": "object", "properties": {
            "tanggal": {"type": "string", "description": "YYYY-MM-DD, kosongkan untuk hari ini."},
        }},
    }},
    {"type": "function", "function": {
        "name": "rute_hari_ini",
        "description": "Rute keliling hari ini: pesanan dikelompokkan per blok, urut Blok A lalu B lalu C lalu D.",
        "parameters": {"type": "object", "properties": {
            "tanggal": {"type": "string", "description": "YYYY-MM-DD, kosongkan untuk hari ini."},
        }},
    }},
    {"type": "function", "function": {
        "name": "tagihan_belum_bayar",
        "description": "Daftar semua pesanan yang belum dibayar, semua tanggal.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "tandai_lunas",
        "description": "Tandai satu pesanan sebagai lunas.",
        "parameters": {"type": "object", "properties": {
            "pesanan_id": {"type": "integer"},
        }, "required": ["pesanan_id"]},
    }},
    {"type": "function", "function": {
        "name": "rekap_omzet",
        "description": "Omzet pada rentang tanggal (default 7 hari terakhir).",
        "parameters": {"type": "object", "properties": {
            "mulai": {"type": "string", "description": "YYYY-MM-DD."},
            "sampai": {"type": "string", "description": "YYYY-MM-DD."},
        }},
    }},
]

_TOOL_DISPATCH = {
    "cari_pelanggan": lambda args, db: tools_mod.cari_pelanggan(
        args["nama"], db_path=db),
    "daftar_harga": lambda args, db: tools_mod.daftar_harga(db_path=db),
    "catat_pesanan": lambda args, db: tools_mod.catat_pesanan(
        args["nama"], args["blok"], args["items"], db_path=db),
    "rekap_harian": lambda args, db: tools_mod.rekap_harian(
        args.get("tanggal") or None, db_path=db),
    "rute_hari_ini": lambda args, db: tools_mod.rute_hari_ini(
        args.get("tanggal") or None, db_path=db),
    "tagihan_belum_bayar": lambda args, db: tools_mod.tagihan_belum_bayar(
        db_path=db),
    "tandai_lunas": lambda args, db: tools_mod.tandai_lunas(
        args["pesanan_id"], db_path=db),
    "rekap_omzet": lambda args, db: tools_mod.rekap_omzet(
        args.get("mulai"), args.get("sampai"), db_path=db),
}

_JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def _call_model(messages, use_tools=True, max_tokens=1024):
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    if use_tools:
        payload["tools"] = OPENAI_TOOLS
        payload["tool_choice"] = "auto"
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    add_surrogate_to_request(req, "custom.baseten",
                             allowed_hosts=["inference.baseten.co"])
    try:
        with urllib.request.build_opener().open(req, timeout=180) as resp:
            data = read_json_response(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"Baseten API error {exc.code}: {detail}") from exc
    msg = data["choices"][0]["message"]
    return msg.get("content") or "", msg.get("tool_calls") or []


def _execute(name, args, db_path):
    fn = _TOOL_DISPATCH.get(name)
    if fn is None:
        return {"error": f"Tool '{name}' tidak dikenal."}
    try:
        return fn(args, db_path)
    except (ValueError, KeyError, TypeError) as exc:
        return {"error": str(exc)}


def run_turn(user_message, history=None, db_path=None, max_iterations=4):
    """Satu giliran chat: kembalikan {reply, tool_calls, path}."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": user_message})
    executed = []
    path = "direct"
    for _ in range(max_iterations):
        content, tool_calls = _call_model(messages, use_tools=True)
        if tool_calls:
            path = "tool_calls"
            messages.append({"role": "assistant", "content": content,
                             "tool_calls": tool_calls})
            for call in tool_calls:
                fn = call["function"]
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = _execute(fn["name"], args, db_path)
                executed.append({"tool": fn["name"], "args": args,
                                 "result": result})
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                })
            continue
        match = _JSON_BLOCK.search(content)
        if match:
            try:
                action = json.loads(match.group(1))
            except json.JSONDecodeError:
                action = None
            if action and action.get("action") in _TOOL_DISPATCH:
                path = "json_fallback"
                result = _execute(action["action"], action.get("args") or {},
                                  db_path)
                executed.append({"tool": action["action"],
                                 "args": action.get("args") or {},
                                 "result": result})
                messages.append({
                    "role": "user",
                    "content": ("Tool result for "
                                f"{action['action']}: "
                                f"{json.dumps(result, ensure_ascii=False)}. "
                                "Now reply in Bahasa Indonesia."),
                })
                continue
        return {"reply": content, "tool_calls": executed, "path": path}
    return {"reply": messages[-1].get("content", "") if messages else "",
            "tool_calls": executed, "path": path}
