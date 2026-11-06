#!/usr/bin/env python3
"""BangSayur Web App — chat WA-style di atas agen yang sama.

Server stdlib-only (tanpa framework), port 8001:
  GET  /                -> webapp/index.html (chat WARGA saja)
  GET  /vendor          -> webapp/vendor.html (dashboard TUKANG SAYUR, PIN-gated)
  GET  /api/pelanggan   -> daftar pelanggan seed (untuk picker "Saya:")
  POST /api/chat        -> {"sender": "Bu Sari", "message": "..."} -> {"reply": "..."}
  GET  /api/vendor/ringkasan | /api/vendor/menunggu | /api/vendor/komplain
  POST /api/vendor/acc | /api/vendor/lunas | /api/vendor/diantar
       | /api/vendor/harga | /api/vendor/status
  Semua /api/vendor/* wajib PIN vendor (query ?pin=, header
  X-Vendor-Pin, atau field "pin" di body JSON); PIN salah -> 403 dan
  tidak ada data yang dikembalikan. PIN demo "1234" hanya kalau
  BANGSAYUR_VENDOR_PIN tidak diset.

Agen = agent.run_turn yang sama seperti runner Switch (Muse Spark via
Baseten + tools SQLite). JANGAN unset proxy env: panggilan Baseten harus
lewat proxy egress VM (lihat agent/run.py).

DB: data/webapp.db (terpisah dari data/bangsayur.db supaya demo web mulai
bersih; skema + seed sama via db.init_db).
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.abspath(os.path.join(HERE, "..", "agent"))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, AGENT_DIR)

from agent import run_turn, VENDOR_SENDERS, _vendor_ids  # noqa: E402
import db as db_mod  # noqa: E402
import tools as tools_mod  # noqa: E402

# PIN vendor untuk perintah tukang sayur di web app (env BANGSAYUR_VENDOR_PIN).
# Kalau env diset: PIN wajib dan harus sama persis.
# Kalau env TIDAK diset = MODE DEMO: perintah vendor diizinkan tanpa PIN
# (seperti sebelumnya) dan PIN demo "1234" juga diterima; PIN lain ditolak.
# Di produksi WAJIB set BANGSAYUR_VENDOR_PIN sendiri yang kuat — "1234"
# HANYA fallback demo, JANGAN dipakai sebagai PIN produksi.
DEMO_VENDOR_PIN = "1234"
VENDOR_PIN = os.environ.get("BANGSAYUR_VENDOR_PIN") or ""


def _is_vendor_sender(sender):
    """Apakah pengirim ini nama vendor (berdasarkan nama saja).

    Web tidak punya user ID Mattermost, jadi di sini hanya nama yang bisa
    dicek; gerbang sebenarnya adalah PIN di _vendor_pin_ok di bawah.
    """
    return (sender or "").strip().lower() in VENDOR_SENDERS


def _vendor_pin_ok(sender, pin):
    """Cek PIN untuk pengirim vendor di /api/chat.

    Warga biasa: selalu ok (tidak butuh PIN). Vendor: kalau
    BANGSAYUR_VENDOR_PIN diset, pin harus sama persis; kalau tidak diset
    (mode demo), pin kosong (tidak dikirim) atau "1234" diterima.
    PIN tidak pernah di-log di sini.
    """
    if not _is_vendor_sender(sender):
        return True
    if VENDOR_PIN:
        return (pin or "") == VENDOR_PIN
    return (pin or "") in ("", DEMO_VENDOR_PIN)


def _api_vendor_pin_ok(pin):
    """Cek PIN untuk endpoint /api/vendor/*.

    Berbeda dari /api/chat (yang di mode demo membolehkan tanpa PIN):
    dashboard vendor SELALU minta PIN. Kalau BANGSAYUR_VENDOR_PIN diset,
    PIN harus sama persis; kalau tidak diset (mode demo), PIN harus
    "1234". PIN salah -> 403 dan tidak ada data yang dikembalikan.
    PIN tidak pernah di-log.
    """
    if VENDOR_PIN:
        return (pin or "") == VENDOR_PIN
    return (pin or "") == DEMO_VENDOR_PIN


def _web_sender_id(sender, sender_id):
    """ID pengirim untuk run_turn.

    Web tidak punya user ID Mattermost. Kalau pengirim vendor sudah lolos
    cek PIN dan BANGSAYUR_VENDOR_IDS diset, pakai ID vendor pertama yang
    dikonfigurasi sebagai identitas sesi web — kalau tidak, _is_vendor di
    agent.py akan menolak nama "Tukang Sayur" saja saat daftar ID diset.
    Di mode demo (daftar ID kosong) kembalikan apa adanya (None) supaya
    fallback nama tetap berlaku.
    """
    if sender_id:
        return sender_id
    if not _is_vendor_sender(sender):
        return None
    ids = _vendor_ids()
    return sorted(ids)[0] if ids else None

WEBAPP_DB = os.path.join(REPO_ROOT, "data", "webapp.db")
PORT = int(os.environ.get("BANGSAYUR_WEB_PORT", "8001"))
HISTORY = {}  # sender -> list[{role, content}], maks 10 giliran terakhir

# Key Baseten: di VM ini pakai Secure Vault surrogate (agent.py). Di VPS,
# agent.py fallback ke env BASENTEN_API_KEY — kalau env kosong, coba baca
# file key yang sudah ada dari deploy MejaBahasa (~/mejabahasa/.baseten_key).
if not os.environ.get("BASENTEN_API_KEY"):
    for _kf in (os.path.expanduser("~/mejabahasa/.baseten_key"),
                os.path.expanduser("~/.baseten_key")):
        try:
            with open(_kf) as _f:
                _k = _f.read().strip()
            if _k:
                os.environ["BASENTEN_API_KEY"] = _k
                break
        except OSError:
            continue


def _history(sender):
    return HISTORY.setdefault(sender, [])


def _push_history(sender, user_msg, reply):
    h = _history(sender)
    h.append({"role": "user", "content": user_msg})
    h.append({"role": "assistant", "content": reply})
    HISTORY[sender] = h[-20:]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # diam, jangan spam log
        pass

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, ctype):
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _pin_from_request(self, data=None):
        """PIN vendor dari body JSON, header X-Vendor-Pin, atau ?pin=."""
        if data and data.get("pin") is not None:
            return str(data.get("pin"))
        hdr = self.headers.get("X-Vendor-Pin")
        if hdr:
            return hdr
        qs = parse_qs(urlparse(self.path).query)
        return (qs.get("pin") or [""])[0]

    def _read_json_body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return None

    def _vendor_get(self, p):
        """GET /api/vendor/* — semua PIN-gated (403 kalau PIN salah)."""
        pin = self._pin_from_request()
        if not _api_vendor_pin_ok(pin):
            return self._send_json({"error": "PIN vendor salah."}, 403)
        if p == "/api/vendor/ringkasan":
            return self._send_json({
                "ok": True,
                "menunggu": tools_mod.daftar_menunggu_acc(WEBAPP_DB),
                "rekap": tools_mod.rekap_harian(db_path=WEBAPP_DB),
                "tagihan": tools_mod.tagihan_belum_bayar(db_path=WEBAPP_DB),
                "rute": tools_mod.rute_hari_ini(db_path=WEBAPP_DB),
                "harga": tools_mod.daftar_harga(WEBAPP_DB),
                "status_toko": tools_mod.cek_status_toko(db_path=WEBAPP_DB),
            })
        if p == "/api/vendor/menunggu":
            return self._send_json(
                tools_mod.daftar_menunggu_acc(WEBAPP_DB))
        if p == "/api/vendor/komplain":
            return self._send_json(tools_mod.daftar_komplain(db_path=WEBAPP_DB))
        self.send_error(404, "not found")

    def _vendor_post(self, p, data):
        """POST /api/vendor/* — semua PIN-gated, panggil tools langsung
        (bukan lewat LLM): PIN adalah auth-nya, jadi tools di sini
        dijalankan sebagai vendor yang sah."""
        if data is None:
            return self._send_json({"error": "body JSON tidak valid"}, 400)
        if not _api_vendor_pin_ok(self._pin_from_request(data)):
            return self._send_json({"error": "PIN vendor salah."}, 403)
        try:
            pid = data.get("pesanan_id")
            pid = int(pid) if pid is not None else None
        except (TypeError, ValueError):
            return self._send_json(
                {"ok": False, "error": "pesanan_id harus angka."}, 400)
        if p == "/api/vendor/acc":
            aksi = (data.get("aksi") or "").strip().lower()
            if pid is None or aksi not in ("acc", "tolak", "dp_masuk"):
                return self._send_json(
                    {"ok": False,
                     "error": "Butuh pesanan_id dan aksi acc/tolak/dp_masuk."},
                    400)
            return self._send_json(
                tools_mod.konfirmasi_pesanan(pid, aksi, db_path=WEBAPP_DB))
        if p == "/api/vendor/lunas":
            if pid is None:
                return self._send_json(
                    {"ok": False, "error": "Butuh pesanan_id."}, 400)
            return self._send_json(tools_mod.tandai_lunas(
                pid, data.get("metode"), db_path=WEBAPP_DB))
        if p == "/api/vendor/diantar":
            if pid is None:
                return self._send_json(
                    {"ok": False, "error": "Butuh pesanan_id."}, 400)
            return self._send_json(
                tools_mod.tandai_diantar(pid, db_path=WEBAPP_DB))
        if p == "/api/vendor/harga":
            nama = (data.get("nama_item") or "").strip()
            if not nama:
                return self._send_json(
                    {"ok": False, "error": "Butuh nama_item."}, 400)
            return self._send_json(tools_mod.atur_harga_stok(
                nama, data.get("harga"), data.get("stok"),
                db_path=WEBAPP_DB))
        if p == "/api/vendor/status":
            status = (data.get("status") or "").strip().lower()
            if status not in ("buka", "libur"):
                return self._send_json(
                    {"ok": False, "error": "Status harus buka atau libur."},
                    400)
            hasil = tools_mod.atur_status_toko(
                status, data.get("pesan") or "", db_path=WEBAPP_DB)
            jam = (data.get("jam_cutoff") or "").strip()
            if jam and hasil.get("ok"):
                cutoff = tools_mod.atur_cutoff(jam, db_path=WEBAPP_DB)
                hasil = dict(hasil)
                hasil["cutoff"] = cutoff
                if not cutoff.get("ok"):
                    return self._send_json(hasil, 400)
            return self._send_json(hasil)
        self.send_error(404, "not found")

    def do_GET(self):
        p = urlparse(self.path).path
        if p in ("/", "/index.html"):
            return self._send_file(os.path.join(HERE, "index.html"), "text/html; charset=utf-8")
        if p in ("/vendor", "/vendor.html"):
            return self._send_file(os.path.join(HERE, "vendor.html"), "text/html; charset=utf-8")
        if p == "/api/pelanggan":
            conn = db_mod.connect(WEBAPP_DB)
            rows = conn.execute(
                "SELECT nama, blok, alamat FROM pelanggan ORDER BY blok, nama"
            ).fetchall()
            conn.close()
            return self._send_json({"pelanggan": [dict(r) for r in rows]})
        if p == "/api/harga":
            return self._send_json(tools_mod.daftar_harga(WEBAPP_DB))
        if p.startswith("/api/vendor/"):
            return self._vendor_get(p)
        self.send_error(404, "not found")

    def do_POST(self):
        p = urlparse(self.path).path
        if p.startswith("/api/vendor/"):
            return self._vendor_post(p, self._read_json_body())
        if p != "/api/chat":
            return self.send_error(404, "not found")
        data = self._read_json_body()
        if data is None:
            return self._send_json({"error": "body JSON tidak valid"}, 400)
        sender = (data.get("sender") or "").strip() or "Warga"
        message = (data.get("message") or "").strip()
        if not message:
            return self._send_json({"error": "pesan kosong"}, 400)
        # Gerbang PIN vendor: pengirim bernama vendor (mis. "Tukang Sayur")
        # wajib PIN yang benar kalau BANGSAYUR_VENDOR_PIN diset; di mode
        # demo (env kosong) diizinkan seperti sebelumnya. Warga biasa
        # tidak butuh PIN. PIN tidak pernah di-log.
        pin = data.get("pin")
        if not _vendor_pin_ok(sender, pin):
            return self._send_json(
                {"reply": "Maaf, perintah tukang sayur butuh PIN vendor "
                          "yang benar."})
        sender_id = _web_sender_id(
            sender, (data.get("sender_id") or "").strip() or None)
        try:
            result = run_turn(f"{sender}: {message}",
                              history=list(_history(sender)), db_path=WEBAPP_DB,
                              sender=sender, sender_id=sender_id)
            reply = result.get("reply") or "Maaf, saya tidak mengerti."
        except Exception as e:
            print(f"[web] run_turn gagal: {e}", flush=True)
            reply = "Waduh, saya lagi error bentar. Coba ulangi pesannya ya."
        _push_history(sender, message, reply)
        self._send_json({"reply": reply})


if __name__ == "__main__":
    db_mod.init_db(WEBAPP_DB)
    print(f"BangSayur web app: http://127.0.0.1:{PORT}  (DB: {WEBAPP_DB})", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
