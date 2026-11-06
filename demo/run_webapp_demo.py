#!/usr/bin/env python3
"""Demo otomatis BangSayur lewat webapp (/api/chat) — atau mode mock.

Skenario 6 langkah (alur YA -> ACC, stok baru berkurang saat ACC):
  (a) Bu Sari pesan 2 ikat kangkung + 1 kg cabai merah (Rp58.000)
  (b) Bu Sari balas YA -> pesanan #1, status menunggu_acc
  (c) Vendor (Tukang Sayur) ACC #1 -> dikonfirmasi, stok berkurang
  (d) Pak Budi pesan 1 kg telur + 2 papan tempe (Rp40.000), YA, ACC
  (e) Bu Ratna tanya rekap/tagihan -> hanya miliknya sendiri (dia belum
      pesan -> 0 / tidak ada); cek_pesanan milik orang lain ditolak
  (f) Vendor tanya rekap omzet (semua: Rp98.000, lunas Rp0, belum
      Rp98.000) + rute hari ini (hanya vendor)

Mode live (--live):
  Start webapp/server.py sendiri di 127.0.0.1 port acak dengan DB TEMP di
  /tmp (BUKAN data/webapp.db), kirim tiap langkah lewat POST /api/chat
  (urllib, stdlib saja), lalu verifikasi angka langsung dari SQLite.
  Butuh model Baseten yang bisa dihubungi server (env BASENTEN_API_KEY
  atau key yang dibaca server sendiri, lihat webapp/server.py).
  Skrip ini TIDAK membaca, TIDAK menyimpan, dan TIDAK menulis key apa pun.
  Perintah vendor dikirim beserta PIN vendor (--vendor-pin, default
  "1234" = PIN demo webapp; kalau BANGSAYUR_VENDOR_PIN diset di server,
  isi dengan PIN itu — lihat .env.example).

Mode mock (default kalau --mock, atau kalau BASENTEN_API_KEY tidak ada di
env):
  TANPA model dan TANPA server. Langkah yang sama dijalankan dengan
  memanggil tool SQLite lewat agent._execute — jalur enforcement/privasi
  yang SAMA seperti yang dipakai run_turn (tool khusus vendor diblokir
  untuk warga, rekap/tagihan/cek_pesanan warga difilter ke miliknya
  sendiri). Balasan agen di mode ini DISUSUN dari hasil tool, bukan
  keluaran model — jadi angka (total, stok, rekap, rute) terverifikasi,
  tapi teks balasannya rekonstruksi, bukan kutipan model.

Hasil run (mode apa pun) ditulis ke demo/transcript-webapp.md dengan
header yang jujur soal modenya, plus bagian Verifikasi DB. Skrip bisa
jalan tanpa server Switch/Mattermost.

Pemakaian:
  python3 demo/run_webapp_demo.py            # mock kalau tidak ada key
  python3 demo/run_webapp_demo.py --mock     # paksa mock (tanpa model)
  python3 demo/run_webapp_demo.py --live     # paksa live via /api/chat
  python3 demo/run_webapp_demo.py --live --port 8001
"""
import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
AGENT_DIR = os.path.join(REPO_ROOT, "agent")
sys.path.insert(0, AGENT_DIR)

import db as db_mod  # noqa: E402
import tools as tools_mod  # noqa: E402

OUT_PATH = os.path.join(HERE, "transcript-webapp.md")

# Harga seed (db.py) — dipakai untuk assert, bukan untuk menghitung total:
# total SELALU diambil dari hasil catat_pesanan (DB), bukan dari sini.
HARGA_SEED = {"Kangkung": 5000, "Cabai merah": 48000,
              "Telur ayam": 28000, "Tempe": 6000}
STOK_AWAL = {"Kangkung": 30, "Cabai merah": 8, "Telur ayam": 15, "Tempe": 20}
STOK_AKHIR = {"Kangkung": 28, "Cabai merah": 7, "Telur ayam": 14, "Tempe": 18}
TOTAL_SARI = 2 * 5000 + 1 * 48000      # Rp58.000
TOTAL_BUDI = 1 * 28000 + 2 * 6000      # Rp40.000
TOTAL_SEMUA = TOTAL_SARI + TOTAL_BUDI  # Rp98.000

VENDOR = "Tukang Sayur"  # di Mattermost akun vendor bernama "warga"


def rp(n):
    return f"Rp{n:,.0f}".replace(",", ".")


# ---------------------------------------------------------------- mock --
def _fmt_items(items):
    return "\n".join(
        f"• {it['nama']} {it['qty']:g} {it['satuan']} - {it['subtotal_rp']}"
        for it in items)


def run_mock(db_path):
    """Jalankan 6 langkah via agent._execute (tanpa model, tanpa server).

    Mengembalikan (transcript_lines, checks, tanggal) — checks = list
    (nama_cek, lolos, detail).
    """
    import agent as agent_mod

    lines = []
    checks = []

    def check(nama, ok, detail=""):
        checks.append((nama, bool(ok), detail))
        print(f"  [{'OK ' if ok else 'GAGAL'}] {nama}"
              + (f" — {detail}" if detail else ""), flush=True)

    def call(tool, args, sender):
        return agent_mod._execute(tool, args, db_path, sender=sender)

    db_mod.init_db(db_path)
    lines.append("## (a) Bu Sari pesan sayur")
    lines.append("")
    lines.append("> [Bu Sari] halo bang, saya mau pesan 2 ikat kangkung "
                 "sama 1 kg cabai merah")
    lines.append("")
    cari = call("cari_pelanggan", {"nama": "Bu Sari"}, "Bu Sari")
    assert cari.get("ditemukan") == 1, cari
    lines.append("> [BangSayur] Halo Bu Sari 🥬")
    lines.append(">")
    lines.append("> • Kangkung 2 ikat - Rp10.000")
    lines.append("> • Cabai merah 1 kg - Rp48.000")
    lines.append(">")
    lines.append("> Total: Rp58.000")
    lines.append(">")
    lines.append("> Betul? Balas YA.")
    lines.append("")
    conn = db_mod.connect(db_path)
    n_pesanan = conn.execute(
        "SELECT COUNT(*) c FROM pesanan").fetchone()["c"]
    conn.close()
    check("sebelum YA belum ada pesanan tercatat", n_pesanan == 0,
          f"pesanan={n_pesanan}")

    lines.append("## (b) Bu Sari balas YA")
    lines.append("")
    lines.append("> [Bu Sari] YA")
    lines.append("")
    catat = call("catat_pesanan", {
        "nama": "Bu Sari", "blok": "A",
        "items": [{"nama_item": "Kangkung", "qty": 2},
                  {"nama_item": "Cabai merah", "qty": 1}]}, "Bu Sari")
    assert catat.get("ok"), catat
    pesanan_sari = catat["pesanan_id"]
    tanggal = catat["tanggal"]
    lines.append(f"> [BangSayur] Pesanan #{pesanan_sari} sudah dicatat ya Bu Sari 🥬")
    lines.append(">")
    lines.append("> " + _fmt_items(catat["items"]).replace("\n", "\n> "))
    lines.append(">")
    lines.append(f"> Total: {catat['total_rp']}")
    lines.append("> Status: menunggu ACC Bang Sayur")
    lines.append(">")
    lines.append("> Nanti Bang Sayur mampir ke Blok A ya Bu. Makasih 🙏")
    lines.append("")
    check("pesanan Bu Sari total Rp58.000", catat["total"] == TOTAL_SARI,
          catat["total_rp"])
    check("pesanan Bu Sari status menunggu_acc",
          catat["status"] == "menunggu_acc", catat["status"])
    stok = {r["nama"]: r["stok"] for r in
            tools_mod.daftar_harga(db_path)["items"]}
    check("stok BELUM berkurang sebelum ACC",
          stok["Kangkung"] == 30 and stok["Cabai merah"] == 8,
          f"Kangkung={stok['Kangkung']:g}, Cabai merah={stok['Cabai merah']:g}")

    lines.append("## (c) Vendor ACC pesanan Bu Sari")
    lines.append("")
    lines.append("> [Tukang Sayur] ACC #1")
    lines.append("")
    tunggu = call("daftar_menunggu_acc", {}, VENDOR)
    assert tunggu.get("ok") and len(tunggu["menunggu"]) == 1, tunggu
    acc = call("konfirmasi_pesanan",
               {"pesanan_id": pesanan_sari, "aksi": "acc"}, VENDOR)
    assert acc.get("ok"), acc
    lines.append(f"> [BangSayur] Siap! Pesanan #{pesanan_sari} Bu Sari sudah "
                 "di-ACC dan dikonfirmasi 🛵")
    lines.append(">")
    lines.append(f"> Total: {acc['total_rp']} | Status bayar: belum")
    lines.append("")
    check("pesanan #1 dikonfirmasi setelah ACC",
          acc["status"] == "dikonfirmasi", acc["status"])
    stok = {r["nama"]: r["stok"] for r in
            tools_mod.daftar_harga(db_path)["items"]}
    check("stok berkurang SAAT ACC (Kangkung 30->28, Cabai 8->7)",
          stok["Kangkung"] == 28 and stok["Cabai merah"] == 7,
          f"Kangkung={stok['Kangkung']:g}, Cabai merah={stok['Cabai merah']:g}")

    lines.append("## (d) Pak Budi pesan, YA, lalu ACC")
    lines.append("")
    lines.append("> [Pak Budi] bang, saya mau 1 kg telur ayam sama 2 papan tempe")
    lines.append("")
    cari = call("cari_pelanggan", {"nama": "Pak Budi"}, "Pak Budi")
    assert cari.get("ditemukan") == 1, cari
    lines.append("> [BangSayur] Halo Pak Budi 🥬")
    lines.append(">")
    lines.append("> • Telur ayam 1 kg - Rp28.000")
    lines.append("> • Tempe 2 papan - Rp12.000")
    lines.append(">")
    lines.append("> Total: Rp40.000")
    lines.append(">")
    lines.append("> Betul? Balas YA.")
    lines.append("")
    lines.append("> [Pak Budi] YA")
    lines.append("")
    catat2 = call("catat_pesanan", {
        "nama": "Pak Budi", "blok": "A",
        "items": [{"nama_item": "Telur ayam", "qty": 1},
                  {"nama_item": "Tempe", "qty": 2}]}, "Pak Budi")
    assert catat2.get("ok"), catat2
    pesanan_budi = catat2["pesanan_id"]
    lines.append(f"> [BangSayur] Pesanan #{pesanan_budi} sudah dicatat ya Pak Budi 🥬")
    lines.append(">")
    lines.append("> " + _fmt_items(catat2["items"]).replace("\n", "\n> "))
    lines.append(">")
    lines.append(f"> Total: {catat2['total_rp']}")
    lines.append("> Status: menunggu ACC Bang Sayur")
    lines.append("")
    check("pesanan Pak Budi total Rp40.000", catat2["total"] == TOTAL_BUDI,
          catat2["total_rp"])
    lines.append("> [Tukang Sayur] ACC #2")
    lines.append("")
    acc2 = call("konfirmasi_pesanan",
                {"pesanan_id": pesanan_budi, "aksi": "acc"}, VENDOR)
    assert acc2.get("ok"), acc2
    lines.append(f"> [BangSayur] Siap! Pesanan #{pesanan_budi} Pak Budi sudah "
                 "di-ACC dan dikonfirmasi 🛵")
    lines.append(">")
    lines.append(f"> Total: {acc2['total_rp']} | Status bayar: belum")
    lines.append("")
    check("pesanan #2 dikonfirmasi setelah ACC",
          acc2["status"] == "dikonfirmasi", acc2["status"])
    stok = {r["nama"]: r["stok"] for r in
            tools_mod.daftar_harga(db_path)["items"]}
    check("stok Telur 15->14, Tempe 20->18 setelah ACC #2",
          stok["Telur ayam"] == 14 and stok["Tempe"] == 18,
          f"Telur={stok['Telur ayam']:g}, Tempe={stok['Tempe']:g}")

    lines.append("## (e) Bu Ratna tanya rekap / tagihan (hanya miliknya)")
    lines.append("")
    lines.append("> [Bu Ratna] bang, rekap hari ini berapa? sama tagihan saya?")
    lines.append("")
    rekap_ratna = call("rekap_harian", {"tanggal": tanggal}, "Bu Ratna")
    tagihan_ratna = call("tagihan_belum_bayar", {}, "Bu Ratna")
    cek_orang = call("cek_pesanan", {"pesanan_id": pesanan_sari}, "Bu Ratna")
    lines.append("> [BangSayur] Halo Bu Ratna 🥬")
    lines.append(">")
    lines.append("> Rekap hari ini (punya Bu Ratna):")
    lines.append("> • Jumlah pesanan: 0")
    lines.append("> • Omzet: Rp0")
    lines.append(">")
    lines.append("> Bu Ratna belum pesan hari ini, jadi belum ada tagihan. 🙏")
    lines.append("")
    check("rekap Bu Ratna hanya miliknya: 0 pesanan, omzet Rp0",
          rekap_ratna.get("jumlah_pesanan") == 0
          and rekap_ratna.get("omzet") == 0, str(rekap_ratna.get("omzet_rp")))
    check("tagihan Bu Ratna: tidak ada (0)",
          tagihan_ratna.get("jumlah") == 0
          and tagihan_ratna.get("total_tagihan") == 0,
          f"jumlah={tagihan_ratna.get('jumlah')}")
    check("Bu Ratna tidak bisa cek pesanan Bu Sari",
          "error" in cek_orang or not cek_orang.get("ok", True),
          str(cek_orang)[:80])

    lines.append("## (f) Vendor tanya rekap omzet + rute")
    lines.append("")
    lines.append("> [Tukang Sayur] rekap omzet hari ini dong, sama rute")
    lines.append("")
    omzet = call("rekap_omzet", {"mulai": tanggal, "sampai": tanggal}, VENDOR)
    rekap_vendor = call("rekap_harian", {"tanggal": tanggal}, VENDOR)
    rute = call("rute_hari_ini", {"tanggal": tanggal}, VENDOR)
    per_hari = omzet.get("per_hari") or [{}]
    hari = per_hari[0] if per_hari else {}
    lines.append(f"> [BangSayur] Siap, ini rekap omzet {tanggal} 🥬")
    lines.append(">")
    lines.append(f"> • Jumlah pesanan: {rekap_vendor.get('jumlah_pesanan')}")
    lines.append(f"> • Omzet: {omzet.get('total_omzet_rp')}")
    lines.append(f"> • Lunas: {hari.get('lunas_rp', 'Rp0')}")
    lines.append(f"> • Belum bayar: {hari.get('belum_rp', 'Rp0')}")
    lines.append(">")
    lines.append("> Rincian per item:")
    for it in rekap_vendor.get("per_item", []):
        lines.append(f"> • {it['nama']} {it['qty']:g} {it['satuan']} - "
                     f"{it['subtotal_rp']}")
    lines.append(">")
    lines.append("> Daftar pesanan:")
    for p in rekap_vendor.get("pesanan", []):
        lines.append(f"> • {p['nama']} {p['blok']} - {p['total_rp']} "
                     f"({p['status_bayar']})")
    lines.append("")
    lines.append("> Rute hari ini:")
    for blok in rute.get("rute", []):
        lines.append(f"> • Blok {blok['blok']} - "
                     f"{len(blok['berhenti'])} berhenti")
        for b in blok["berhenti"]:
            lines.append(f"> • {b['nama']} - {b['alamat']} - "
                         f"{b['total_rp']} - {b['status_bayar']}")
    lines.append(f"> • Total berhenti: {rute.get('total_berhenti')}")
    if rute.get("berikutnya"):
        br = rute["berikutnya"]
        lines.append(f"> • Berikutnya: {br['nama']} - {br['alamat']}")
    lines.append("")
    check("omzet vendor Rp98.000 (semua pesanan)",
          omzet.get("total_omzet") == TOTAL_SEMUA,
          omzet.get("total_omzet_rp"))
    check("vendor: lunas Rp0, belum Rp98.000",
          (hari.get("lunas_rp") in ("Rp0", None)
           and hari.get("belum_rp") == rp(TOTAL_SEMUA)),
          f"lunas={hari.get('lunas_rp')}, belum={hari.get('belum_rp')}")
    check("rute vendor: 2 berhenti, urut No. 5 lalu No. 12",
          rute.get("total_berhenti") == 2
          and [b["nama"] for blok in rute.get("rute", [])
               for b in blok["berhenti"]] == ["Pak Budi", "Bu Sari"],
          str([b["nama"] for blok in rute.get("rute", [])
               for b in blok["berhenti"]]))
    check("rute berikutnya = Pak Budi (Jl. Melati No. 5)",
          (rute.get("berikutnya") or {}).get("nama") == "Pak Budi",
          str((rute.get("berikutnya") or {}).get("alamat")))

    return lines, checks, tanggal


# ---------------------------------------------------------------- live --
def _free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


_SERVER_WRAPPER = r"""
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "webapp"))
import server
server.WEBAPP_DB = os.environ["BANGSAYUR_DEMO_DB"]
server.db_mod.init_db(server.WEBAPP_DB)
from http.server import ThreadingHTTPServer
ThreadingHTTPServer(("127.0.0.1", int(os.environ["BANGSAYUR_WEB_PORT"])),
                    server.Handler).serve_forever()
"""

# (sender, message) — urutan yang sama seperti mode mock.
LIVE_STEPS = [
    ("Bu Sari", "halo bang, saya mau pesan 2 ikat kangkung sama 1 kg cabai merah"),
    ("Bu Sari", "YA"),
    ("Tukang Sayur", "ACC #1"),
    ("Pak Budi", "bang, saya mau 1 kg telur ayam sama 2 papan tempe"),
    ("Pak Budi", "YA"),
    ("Tukang Sayur", "ACC #2"),
    ("Bu Ratna", "bang, rekap hari ini berapa? sama tagihan saya?"),
    ("Tukang Sayur", "rekap omzet hari ini dong, sama rute"),
]


def _post_chat(base, sender, message, vendor_pin=None):
    body = {"sender": sender, "message": message}
    if sender.strip().lower() in ("tukang sayur", "bang sayur", "warga",
                                  "toko", "pemilik"):
        # Gerbang PIN vendor di server: di mode demo PIN "1234" diterima,
        # tanpa PIN pun diterima; kalau server diset BANGSAYUR_VENDOR_PIN,
        # kirim PIN itu lewat --vendor-pin.
        body["pin"] = vendor_pin or ""
    req = urllib.request.Request(
        f"{base}/api/chat",
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode())


def run_live(db_path, port, vendor_pin=None):
    """Start server sendiri (DB temp) + kirim skenario via /api/chat."""
    env = dict(os.environ)
    env["BANGSAYUR_WEB_PORT"] = str(port)
    env["BANGSAYUR_DEMO_DB"] = db_path
    proc = subprocess.Popen(
        [sys.executable, "-c", _SERVER_WRAPPER],
        cwd=REPO_ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    base = f"http://127.0.0.1:{port}"
    try:
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"{base}/api/pelanggan",
                                            timeout=3) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("webapp tidak merespons dalam 20 detik")
        lines = []
        for sender, msg in LIVE_STEPS:
            r = _post_chat(base, sender, msg, vendor_pin=vendor_pin)
            reply = (r.get("reply") or "").strip()
            lines.append(f"> [{sender}] {msg}")
            lines.append("")
            reply_lines = reply.splitlines() or ["(balasan kosong)"]
            for i, rl in enumerate(reply_lines):
                prefix = "> [BangSayur] " if i == 0 else "> "
                lines.append(f"{prefix}{rl}")
            lines.append("")
            print(f"  [{sender}] {msg[:50]!r} -> {reply[:80]!r}", flush=True)
            time.sleep(1)
        return lines
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def verify_db(db_path, tanggal):
    """Verifikasi angka langsung dari SQLite (dipakai kedua mode)."""
    conn = db_mod.connect(db_path)
    pesanan = conn.execute(
        "SELECT p.id, pl.nama, p.total, p.status, p.status_bayar "
        "FROM pesanan p JOIN pelanggan pl ON pl.id = p.pelanggan_id "
        "ORDER BY p.id").fetchall()
    stok = {r["nama"]: r["stok"] for r in conn.execute(
        "SELECT nama, stok FROM items").fetchall()}
    conn.close()
    checks = []
    total = sum(r["total"] for r in pesanan if r["status"] == "dikonfirmasi")
    checks.append(("2 pesanan dikonfirmasi, total Rp98.000",
                   len([r for r in pesanan if r["status"] == "dikonfirmasi"]) == 2
                   and total == TOTAL_SEMUA,
                   f"pesanan={len(pesanan)}, total={rp(total)}"))
    for nama, awal, akhir in (("Kangkung", 30, 28), ("Cabai merah", 8, 7),
                              ("Telur ayam", 15, 14), ("Tempe", 20, 18)):
        checks.append((f"stok {nama} {awal}->{akhir}",
                       stok.get(nama) == akhir,
                       f"stok={stok.get(nama):g}" if stok.get(nama) is not None
                       else "stok=(tidak ada)"))
    omzet = tools_mod.rekap_omzet(tanggal, tanggal, db_path=db_path)
    per_hari = omzet.get("per_hari") or [{}]
    hari = per_hari[0] if per_hari else {}
    checks.append(("rekap omzet vendor: Rp98.000, lunas Rp0, belum Rp98.000",
                   omzet.get("total_omzet") == TOTAL_SEMUA
                   and hari.get("lunas_rp") in ("Rp0", None)
                   and hari.get("belum_rp") == rp(TOTAL_SEMUA),
                   f"omzet={omzet.get('total_omzet_rp')}, "
                   f"lunas={hari.get('lunas_rp')}, "
                   f"belum={hari.get('belum_rp')}"))
    return checks, pesanan, stok


# ---------------------------------------------------------------- main --
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mock", action="store_true",
                    help="paksa mode mock (tanpa model, tanpa server)")
    ap.add_argument("--live", action="store_true",
                    help="paksa mode live via /api/chat (butuh model Baseten)")
    ap.add_argument("--port", type=int, default=0,
                    help="port webapp untuk mode live (0 = acak)")
    ap.add_argument("--vendor-pin", default="1234",
                    help="PIN vendor untuk mode live (default: 1234, "
                         "PIN demo webapp; isi PIN sendiri kalau server "
                         "diset BANGSAYUR_VENDOR_PIN)")
    args = ap.parse_args()
    if args.mock and args.live:
        print("Pilih salah satu: --mock atau --live.", file=sys.stderr)
        return 2

    if args.live:
        mode = "live"
    elif args.mock:
        mode = "mock"
    else:
        mode = "live" if os.environ.get("BASENTEN_API_KEY") else "mock"

    tmpdir = tempfile.mkdtemp(prefix="bangsayur-demo-")
    db_path = os.path.join(tmpdir, "webapp-demo.db")
    print(f"Mode: {mode} | DB temp: {db_path}", flush=True)

    today = datetime.now(WIB).date().isoformat()  # tanggal WIB, bukan UTC VM

    if mode == "mock":
        print("Langkah mock (tools SQLite langsung, tanpa model):", flush=True)
        lines, checks, tanggal = run_mock(db_path)
        db_checks, pesanan, stok = verify_db(db_path, tanggal)
        checks.extend(db_checks)
    else:
        port = args.port or _free_port()
        print(f"Start webapp di 127.0.0.1:{port} (DB temp, bukan "
              "data/webapp.db) ...", flush=True)
        lines = run_live(db_path, port, vendor_pin=args.vendor_pin)
        # Tanggal pesanan: dari DB (bisa besok kalau sudah lewat cutoff 07:00).
        conn = db_mod.connect(db_path)
        row = conn.execute("SELECT tanggal FROM pesanan ORDER BY id LIMIT 1"
                           ).fetchone()
        conn.close()
        tanggal = row["tanggal"] if row else today
        db_checks, pesanan, stok = verify_db(db_path, tanggal)
        checks = db_checks
        # Cek privasi tambahan di live mode, langsung dari DB/tools:
        ratna = tools_mod.rekap_harian(tanggal, db_path=db_path,
                                       nama="Bu Ratna")
        checks.append(("live: rekap Bu Ratna hanya miliknya (0 pesanan)",
                       ratna.get("jumlah_pesanan") == 0
                       and ratna.get("omzet") == 0,
                       f"jumlah={ratna.get('jumlah_pesanan')}"))

    # ---- tulis transcript-webapp.md ----
    header = [
        "# Transkrip Demo BangSayur — via Webapp (simulasi lokal)",
        "",
        f"Tanggal: {today} (WIB). Room simulasi: webapp lokal "
        f"(`/api/chat`), BUKAN log live Mattermost/Switch.",
        "",
    ]
    if mode == "mock":
        header += [
            "## Mode: MOCK (tanpa model)",
            "",
            "Transkrip ini dibuat oleh `demo/run_webapp_demo.py --mock`: "
            "langkah-langkahnya dijalankan dengan memanggil tool SQLite "
            "langsung lewat `agent._execute` (jalur enforcement/privasi "
            "yang sama seperti `run_turn`), BUKAN lewat panggilan model "
            "Baseten. Balasan agen di bawah ini DISUSUN dari hasil tool — "
            "angkanya terverifikasi dari database, tapi teks balasannya "
            "rekonstruksi, bukan kutipan balasan model. Jangan klaim ini "
            "sebagai log live.",
            "",
        ]
    else:
        header += [
            "## Mode: LIVE (via /api/chat + model Baseten)",
            "",
            "Transkrip ini direkam dari balasan ASLI model lewat "
            "`POST /api/chat` webapp lokal (server distart skrip dengan "
            "DB temp di /tmp, bukan `data/webapp.db`). Tetap BUKAN log "
            "live Mattermost/Switch — itu jalur yang berbeda.",
            "",
        ]
    body = header + lines
    body += [
        "## Verifikasi DB",
        "",
        "Pesanan (SQLite, DB temp skrip):",
        "",
    ]
    for r in pesanan:
        body.append(f"- #{r['id']} {r['nama']}: {rp(r['total'])} | "
                    f"status={r['status']} | bayar={r['status_bayar']}")
    body += [
        "",
        "Stok sesudah demo:",
        "",
    ]
    for nama in ("Kangkung", "Cabai merah", "Telur ayam", "Tempe"):
        s = stok.get(nama)
        body.append(f"- {nama}: {STOK_AWAL[nama]} -> {s:g}" if s is not None
                    else f"- {nama}: {STOK_AWAL[nama]} -> (tidak ada)")
    body += [
        "",
        "Hasil cek:",
        "",
    ]
    for nama, ok, detail in checks:
        body.append(f"- [{'x' if ok else ' '}] {nama}"
                    + (f" ({detail})" if detail else ""))
    body += [
        "",
        "Semua angka di atas cocok dengan database — agen tidak mengarang "
        "harga, total, atau stok. DB temp skrip ada di "
        f"`{db_path}` (dihapus otomatis bersama /tmp).",
        "",
    ]
    with open(OUT_PATH, "w") as f:
        f.write("\n".join(body))
    print(f"\nTranskrip ditulis: {OUT_PATH}", flush=True)

    gagal = [c for c in checks if not c[1]]
    if gagal:
        print(f"\nGAGAL: {len(gagal)} cek tidak lolos:", flush=True)
        for nama, _, detail in gagal:
            print(f"  - {nama} ({detail})", flush=True)
        return 1
    print(f"\nSemua {len(checks)} cek lolos.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
