#!/usr/bin/env python3
"""BangSayur agent brain: Muse Spark (Baseten) driving the vegetable-vendor tools.

Loop: room message -> model (OpenAI-style tools) -> tools on SQLite -> reply.
Key-nya TIDAK PERNAH ditulis ke file/log/repo: pakai pola Secure Vault yang
sama seperti MejaBahasa (dynamic_credentials surrogate).
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

try:
    sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
    from dynamic_credentials import add_surrogate_to_request, read_json_response
except ImportError:
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
2. ALUR PESANAN (WAJIB, urut):
   a. cari_pelanggan dulu. Kalau TIDAK dikenal: minta nama lengkap + blok +
      alamat, lalu daftar_pelanggan. JANGAN catat pesanan sebelum terdaftar.
   b. Ulangi ringkasan pesanan + total, lalu minta konfirmasi:
      "Betul? Balas YA." JANGAN panggil catat_pesanan sebelum warga balas YA
      (atau kata setuju yang jelas).
   c. Setelah YA, panggil catat_pesanan. Pesanan masuk status MENUNGGU ACC —
      beri tahu warga: "Pesanan #N sudah dicatat, menunggu ACC Bang Sayur."
   d. Kalau pelanggan statusnya 'ditahan' (atau no_show >= 2): JANGAN catat
      biasa. Bilang ordernya perlu DP dulu (transfer), pesanan masuk status
      menunggu_dp dan baru jalan setelah Bang Sayur konfirmasi DP masuk.
3. PERINTAH VENDOR — acc / tolak / dp_masuk / tidak_diambil / lunas HANYA
   dari Bang Sayur sendiri (dikenali dari ID pengirim di
   BANGSAYUR_VENDOR_IDS, atau di mode demo dari nama pengirim "Tukang
   Sayur"). Kalau warga biasa yang minta ACC atau lunas, tolak sopan: itu
   urusan tukang sayur.
   Untuk ACC: cek dulu daftar_menunggu_acc supaya tahu nomor pesanannya.
4. Setiap pesanan yang dicatat status bayarnya 'belum' sampai ada yang bilang
   sudah bayar (tandai_lunas). Jangan pernah bilang "sudah lunas" tanpa tool.
5. Jangan pernah mengarang nomor pesanan, total, atau omzet — hanya dari hasil tool.
6. Kalau stok tidak cukup, bilang sisanya berapa dan tawarkan jumlah yang tersedia
   atau sayur pengganti.
7. Jawab singkat dan padat, cocok dibaca di HP. Kalau ditanya rekap/rute/tagihan,
   tampilkan sebagai daftar, bukan paragraf panjang. Rekap/rute/tagihan/omzet
   HANYA menghitung pesanan yang sudah dikonfirmasi (ACC) — yang masih
   menunggu ACC/DP disebut terpisah.
8. RUTE — rute_hari_ini sudah diurutkan (blok A→B→C→D, di dalam blok per
   jalan lalu nomor rumah) supaya tukang sayur tidak bolak-balik. Tampilkan
   urutan itu apa adanya, jangan diurut ulang. Kalau tukang sayur bilang
   sudah sampai di satu rumah ("sudah diantar #N", "sampai di Bu Sari"),
   panggil tandai_diantar. Kalau dia tanya "berikutnya kemana?", panggil
   rute_berikutnya. Pesanan baru yang di-ACC di tengah jalan langsung masuk
   ke urutan rute yang benar — sebutkan posisinya ke tukang sayur.
9. HARGA/STOK HARIAN — hanya tukang sayur yang boleh mengubah harga/stok.
   Kalau tukang sayur bilang harga naik/turun atau stok berubah, LANGSUNG
   panggil atur_harga_stok — JANGAN bilang tidak bisa atau suruh ke admin.
   Harga di daftar_harga SAMA untuk semua warga, jangan bedakan.
10. GANTI/BATAL — warga boleh ganti isi atau batalkan pesanannya sendiri
    SELAMA masih menunggu ACC/DP. Kalau warga minta ganti/batal, LANGSUNG
    panggil ubah_pesanan / batalkan_pesanan (cocokkan nama pemiliknya) —
    JANGAN lempar ke tukang sayur. Setelah ACC, perubahan harus lewat
    tukang sayur.
11. KOMPLAIN — kalau warga mengeluh (sayur layu, timbangan kurang, salah
    kirim), LANGSUNG panggil catat_komplain, minta maaf singkat, dan bilang
    tukang sayur akan menindaklanjuti. Jangan tanya-tanya dulu. Tukang
    sayur melihatnya lewat daftar_komplain.
12. BAYAR — metode: tunai / transfer / qris. Warga yang bilang sudah
    transfer: panggil lapor_bayar — JANGAN PERNAH panggil tandai_lunas untuk
    warga (tandai_lunas HANYA tukang sayur; sistem memblokir kalau warga
    yang minta). Bon hanya tukang sayur yang bisa (tandai_bon + jatuh
    tempo). Kalau warga bayar tunai dan tanya kembalian, hitung dengan
    hitung_kembalian.
13. TITIP & CATATAN — "titip ke tetangga" atau info lain dicatat dengan
    tambah_catatan dan tampil di rute. Jangan tambahkan catatan sendiri yang
    tidak diminta warga/tukang sayur.
14. LIBUR & BATAS ORDER — SEBELUM menerima pesanan baru, cek cek_status_toko.
    Kalau libur: sampaikan pesannya ke warga dan JANGAN catat pesanan.
    Pesanan yang masuk setelah jam cutoff otomatis jadi pesanan BESOK
    (catat_pesanan mengembalikan untuk_besok=true) — beri tahu warga dengan
    jelas. Atur cutoff/status libur hanya tukang sayur (atur_cutoff /
    atur_status_toko).
15. PRIVASI — JANGAN PERNAH sebutkan alamat atau nomor HP warga lain ke
    warga yang bertanya. Rute lengkap (dengan alamat) HANYA untuk tukang
    sayur. Rekap harian, rekap omzet, dan tagihan belum bayar HANYA untuk
    tukang sayur secara penuh; warga biasa hanya melihat pesanannya
    SENDIRI (sistem memfilter otomatis berdasarkan nama pengirim).
    cek_pesanan warga biasa tidak menampilkan alamat, dan hanya untuk
    pesanannya sendiri.
16. BIAYA & BACKUP — tukang sayur boleh tanya pemakaian AI (cek_biaya:
    jumlah panggilan + token, harga Rupiah tidak ditampilkan karena tarif
    berubah) dan minta backup data (buat_backup) tiap akhir minggu.
17. Kamu hanya urusan sayur dan jualan: pesanan, harga, stok, rute, tagihan,
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
        "name": "daftar_pelanggan",
        "description": "Daftarkan warga baru yang belum dikenal (nama + blok + alamat). WAJIB dipanggil sebelum mencatat pesanan pertama warga baru.",
        "parameters": {"type": "object", "properties": {
            "nama": {"type": "string"},
            "blok": {"type": "string", "enum": ["A", "B", "C", "D"]},
            "alamat": {"type": "string"},
        }, "required": ["nama", "blok"]},
    }},
    {"type": "function", "function": {
        "name": "konfirmasi_pesanan",
        "description": "Keputusan tukang sayur atas satu pesanan. HANYA untuk tukang sayur (pengirim warga/Tukang Sayur). aksi: acc (setujui, stok berkurang), tolak, dp_masuk (DP sudah diterima, lanjut ke menunggu ACC).",
        "parameters": {"type": "object", "properties": {
            "pesanan_id": {"type": "integer"},
            "aksi": {"type": "string", "enum": ["acc", "tolak", "dp_masuk"]},
        }, "required": ["pesanan_id", "aksi"]},
    }},
    {"type": "function", "function": {
        "name": "tandai_tidak_diambil",
        "description": "Tukang sayur sudah sampai tapi warga tidak mengambil pesanan. Stok dikembalikan, no_show pelanggan +1; 2x -> pelanggan ditahan (wajib DP). HANYA untuk tukang sayur.",
        "parameters": {"type": "object", "properties": {
            "pesanan_id": {"type": "integer"},
        }, "required": ["pesanan_id"]},
    }},
    {"type": "function", "function": {
        "name": "daftar_menunggu_acc",
        "description": "Daftar pesanan yang menunggu keputusan tukang sayur (ACC / DP / tolak). Dipakai tukang sayur sebelum ACC.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "cek_pesanan",
        "description": "Detail satu pesanan: status, pelanggan, item, total, status bayar. Tukang sayur melihat semuanya; warga biasa hanya pesanannya sendiri dan tanpa alamat.",
        "parameters": {"type": "object", "properties": {
            "pesanan_id": {"type": "integer"},
        }, "required": ["pesanan_id"]},
    }},
    {"type": "function", "function": {
        "name": "atur_harga_stok",
        "description": "Update harga dan/atau stok satu item (habis belanja pasar). HANYA untuk tukang sayur.",
        "parameters": {"type": "object", "properties": {
            "nama_item": {"type": "string"},
            "harga": {"type": "number"},
            "stok": {"type": "number"},
        }, "required": ["nama_item"]},
    }},
    {"type": "function", "function": {
        "name": "ubah_pesanan",
        "description": "Ganti isi pesanan yang masih menunggu ACC/DP. Total dihitung ulang. Setelah ACC tidak bisa diubah. Kalau nama diisi, harus cocok dengan pemilik pesanan.",
        "parameters": {"type": "object", "properties": {
            "pesanan_id": {"type": "integer"},
            "nama": {"type": "string", "description": "Nama pemilik pesanan, opsional tapi disarankan."},
            "items": {"type": "array", "items": {"type": "object", "properties": {
                "nama_item": {"type": "string"},
                "qty": {"type": "number"}}, "required": ["nama_item", "qty"]}},
        }, "required": ["pesanan_id", "items"]},
    }},
    {"type": "function", "function": {
        "name": "batalkan_pesanan",
        "description": "Batalkan pesanan yang masih menunggu ACC/DP. Kalau nama diisi, harus cocok dengan pemilik pesanan.",
        "parameters": {"type": "object", "properties": {
            "pesanan_id": {"type": "integer"},
            "nama": {"type": "string"},
        }, "required": ["pesanan_id"]},
    }},
    {"type": "function", "function": {
        "name": "catat_komplain",
        "description": "Catat keluhan warga (sayur layu, timbangan kurang, salah kirim) supaya tukang sayur menindaklanjuti.",
        "parameters": {"type": "object", "properties": {
            "nama": {"type": "string"},
            "isi": {"type": "string"},
            "pesanan_id": {"type": "integer"},
        }, "required": ["nama", "isi"]},
    }},
    {"type": "function", "function": {
        "name": "daftar_komplain",
        "description": "Daftar keluhan warga (untuk tukang sayur).",
        "parameters": {"type": "object", "properties": {
            "status": {"type": "string"},
        }},
    }},
    {"type": "function", "function": {
        "name": "tandai_bon",
        "description": "Pesanan dibon (bayar nanti). HANYA untuk tukang sayur, hanya pesanan dikonfirmasi.",
        "parameters": {"type": "object", "properties": {
            "pesanan_id": {"type": "integer"},
            "jatuh_tempo": {"type": "string", "description": "YYYY-MM-DD, opsional."},
        }, "required": ["pesanan_id"]},
    }},
    {"type": "function", "function": {
        "name": "hitung_kembalian",
        "description": "Hitung kembalian tunai dari total tagihan dan uang yang dibayar warga.",
        "parameters": {"type": "object", "properties": {
            "total": {"type": "number"},
            "uang_bayar": {"type": "number"},
        }, "required": ["total", "uang_bayar"]},
    }},
    {"type": "function", "function": {
        "name": "lapor_bayar",
        "description": "Warga melapor sudah bayar (transfer/QRIS/tunai). Hanya menandai 'lapor bayar' — TIDAK otomatis lunas, tukang sayur harus verifikasi lalu tandai_lunas.",
        "parameters": {"type": "object", "properties": {
            "pesanan_id": {"type": "integer"},
            "metode": {"type": "string", "enum": ["transfer", "qris", "tunai"]},
        }, "required": ["pesanan_id", "metode"]},
    }},
    {"type": "function", "function": {
        "name": "tambah_catatan",
        "description": "Tambah catatan ke pesanan, mis. 'titip ke Bu Sari' atau 'timbangan 1,05 kg'. Tampil di rute.",
        "parameters": {"type": "object", "properties": {
            "pesanan_id": {"type": "integer"},
            "catatan": {"type": "string"},
        }, "required": ["pesanan_id", "catatan"]},
    }},
    {"type": "function", "function": {
        "name": "cek_status_toko",
        "description": "Status toko hari ini: buka/libur + pesan + jam batas order. Dicek SEBELUM menerima pesanan baru.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "atur_status_toko",
        "description": "Tukang sayur mengumumkan libur/sakit atau buka lagi. HANYA untuk tukang sayur.",
        "parameters": {"type": "object", "properties": {
            "status": {"type": "string", "enum": ["buka", "libur"]},
            "pesan": {"type": "string"},
        }, "required": ["status"]},
    }},
    {"type": "function", "function": {
        "name": "atur_cutoff",
        "description": "Atur jam batas order (HH:MM). Pesanan setelah jam ini otomatis jadi pesanan besok. HANYA untuk tukang sayur.",
        "parameters": {"type": "object", "properties": {
            "jam": {"type": "string"},
        }, "required": ["jam"]},
    }},
    {"type": "function", "function": {
        "name": "buat_backup",
        "description": "Salin seluruh isi database ke file JSON backup. Dipakai tukang sayur tiap akhir minggu / sebelum ganti HP.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "cek_biaya",
        "description": "Pemakaian AI hari ini (jumlah panggilan + total token). Dipakai tukang sayur untuk memantau biaya jalan.",
        "parameters": {"type": "object", "properties": {
            "tanggal": {"type": "string", "description": "YYYY-MM-DD, kosongkan untuk hari ini."},
        }},
    }},
    {"type": "function", "function": {
        "name": "catat_pesanan",
        "description": "Catat pesanan baru SETELAH warga konfirmasi YA. Pelanggan HARUS sudah terdaftar. Pesanan masuk status menunggu_acc (atau menunggu_dp kalau pelanggan ditahan). Stok TIDAK berkurang di sini — baru berkurang saat tukang sayur ACC.",
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
        "description": "Rekap pesanan hari ini (atau tanggal tertentu): jumlah pesanan, total per item, omzet. Tukang sayur melihat semuanya; warga biasa hanya pesanannya sendiri.",
        "parameters": {"type": "object", "properties": {
            "tanggal": {"type": "string", "description": "YYYY-MM-DD, kosongkan untuk hari ini."},
        }},
    }},
    {"type": "function", "function": {
        "name": "tandai_diantar",
        "description": "Tandai satu berhenti sudah diantar (tukang sayur sudah sampai di rumah warga). HANYA untuk tukang sayur, hanya pesanan dikonfirmasi.",
        "parameters": {"type": "object", "properties": {
            "pesanan_id": {"type": "integer"},
        }, "required": ["pesanan_id"]},
    }},
    {"type": "function", "function": {
        "name": "rute_berikutnya",
        "description": "Berhenti berikutnya hari ini yang belum diantar, sesuai urutan rute. Dipakai tukang sayur di tengah jalan.",
        "parameters": {"type": "object", "properties": {}},
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
        "description": "Daftar pesanan yang belum dibayar, semua tanggal. Tukang sayur melihat semuanya; warga biasa hanya tagihannya sendiri.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "tandai_lunas",
        "description": "Tandai satu pesanan sebagai lunas. HANYA untuk tukang sayur.",
        "parameters": {"type": "object", "properties": {
            "pesanan_id": {"type": "integer"},
            "metode": {"type": "string", "enum": ["tunai", "transfer", "qris"],
                       "description": "Metode bayar, opsional."},
        }, "required": ["pesanan_id"]},
    }},
    {"type": "function", "function": {
        "name": "rekap_omzet",
        "description": "Omzet pada rentang tanggal (default 7 hari terakhir). Tukang sayur melihat semuanya; warga biasa hanya total belanjanya sendiri.",
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
    "tandai_diantar": lambda args, db: tools_mod.tandai_diantar(
        args["pesanan_id"], db_path=db),
    "rute_berikutnya": lambda args, db: tools_mod.rute_berikutnya(
        db_path=db),
    "tagihan_belum_bayar": lambda args, db: tools_mod.tagihan_belum_bayar(
        db_path=db),
    "tandai_lunas": lambda args, db: tools_mod.tandai_lunas(
        args["pesanan_id"], args.get("metode"), db_path=db),
    "tandai_bon": lambda args, db: tools_mod.tandai_bon(
        args["pesanan_id"], args.get("jatuh_tempo"), db_path=db),
    "hitung_kembalian": lambda args, db: tools_mod.hitung_kembalian(
        args["total"], args["uang_bayar"], db_path=db),
    "lapor_bayar": lambda args, db: tools_mod.lapor_bayar(
        args["pesanan_id"], args["metode"], db_path=db),
    "tambah_catatan": lambda args, db: tools_mod.tambah_catatan(
        args["pesanan_id"], args["catatan"], db_path=db),
    "atur_harga_stok": lambda args, db: tools_mod.atur_harga_stok(
        args["nama_item"], args.get("harga"), args.get("stok"), db_path=db),
    "ubah_pesanan": lambda args, db: tools_mod.ubah_pesanan(
        args["pesanan_id"], args["items"], db_path=db,
        nama=args.get("nama")),
    "batalkan_pesanan": lambda args, db: tools_mod.batalkan_pesanan(
        args["pesanan_id"], args.get("nama"), db_path=db),
    "catat_komplain": lambda args, db: tools_mod.catat_komplain(
        args["nama"], args["isi"], args.get("pesanan_id"), db_path=db),
    "daftar_komplain": lambda args, db: tools_mod.daftar_komplain(
        args.get("status"), db_path=db),
    "cek_status_toko": lambda args, db: tools_mod.cek_status_toko(
        db_path=db),
    "atur_status_toko": lambda args, db: tools_mod.atur_status_toko(
        args["status"], args.get("pesan") or "", db_path=db),
    "atur_cutoff": lambda args, db: tools_mod.atur_cutoff(
        args["jam"], db_path=db),
    "buat_backup": lambda args, db: tools_mod.buat_backup(db_path=db),
    "cek_biaya": lambda args, db: tools_mod.cek_biaya(
        args.get("tanggal"), db_path=db),
    "daftar_pelanggan": lambda args, db: tools_mod.daftar_pelanggan(
        args["nama"], args["blok"], args.get("alamat") or "", db_path=db),
    "konfirmasi_pesanan": lambda args, db: tools_mod.konfirmasi_pesanan(
        args["pesanan_id"], args["aksi"], db_path=db),
    "tandai_tidak_diambil": lambda args, db: tools_mod.tandai_tidak_diambil(
        args["pesanan_id"], db_path=db),
    "daftar_menunggu_acc": lambda args, db: tools_mod.daftar_menunggu_acc(
        db_path=db),
    "cek_pesanan": lambda args, db: tools_mod.cek_pesanan(
        args["pesanan_id"], db_path=db),
    "rekap_omzet": lambda args, db: tools_mod.rekap_omzet(
        args.get("mulai"), args.get("sampai"), db_path=db),
}

_JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


# HTTP 429/500/502/503 boleh dicoba ulang; 400/401/404 TIDAK (percuma).
# Backoff 1 dtk sebelum percobaan ke-2, 2 dtk sebelum percobaan ke-3.
_RETRYABLE_CODES = {429, 500, 502, 503}
_RETRY_BACKOFFS = (1, 2)


def _call_model(messages, use_tools=True, max_tokens=1024, db_path=None):
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
    # Retry 2x (total 3 percobaan) hanya untuk 429/500/502/503 (rate limit
    # atau galat server sementara). 400/401/404 langsung raise.
    # Timeout 180 dtk per percobaan, seperti sebelumnya.
    data = None
    for attempt in range(3):
        try:
            with urllib.request.build_opener().open(req, timeout=180) as resp:
                data = read_json_response(resp)
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            err = RuntimeError(f"Baseten API error {exc.code}: {detail}")
            if exc.code in _RETRYABLE_CODES and attempt < 2:
                print(f"[agent] Baseten {exc.code}, retry {attempt + 1}/2 "
                      f"dalam {_RETRY_BACKOFFS[attempt]} dtk", flush=True)
                time.sleep(_RETRY_BACKOFFS[attempt])
                continue
            raise err from exc
    msg = data["choices"][0]["message"]
    # Catat pemakaian token (best-effort, jangan rusak balasan kalau gagal).
    try:
        usage = data.get("usage") or {}
        if usage.get("total_tokens"):
            tools_mod.catat_pemakaian(usage.get("prompt_tokens", 0),
                                      usage.get("completion_tokens", 0),
                                      db_path=db_path)
    except Exception:
        pass
    return msg.get("content") or "", msg.get("tool_calls") or []


# Tools yang HANYA boleh dijalankan atas perintah tukang sayur.
# Dienforce di _execute (bukan cuma di prompt) supaya warga tidak bisa
# menandai lunas sendiri / mengubah harga / ACC pesanan orang lewat chat.
# Vendor dikenali dari ID pengirim (BANGSAYUR_VENDOR_IDS) — lihat
# _is_vendor. Kalau daftar ID kosong (mode demo), fallback ke nama
# pengirim di VENDOR_SENDERS; itu DEMO-ONLY, nama pengirim bisa dipalsu
# siapa pun, JANGAN dipakai di produksi nyata.
VENDOR_TOOLS = {
    "konfirmasi_pesanan", "tandai_lunas", "tandai_bon",
    "tandai_tidak_diambil", "tandai_diantar", "atur_harga_stok",
    "atur_status_toko", "atur_cutoff", "daftar_komplain",
    "daftar_menunggu_acc", "buat_backup", "cek_biaya", "rute_hari_ini",
    # Data penuh (semua warga) hanya untuk vendor; warga biasa mendapat
    # versi yang difilter/diredaksi — lihat _execute / SCOPED_TOOLS.
    "cek_pesanan", "rekap_omzet", "rekap_harian", "tagihan_belum_bayar",
}
# Subset VENDOR_TOOLS yang punya versi aman untuk warga biasa:
# rekap/tagihan difilter ke pesanan pengirim sendiri, cek_pesanan
# diredaksi (tanpa alamat) dan hanya untuk pesanan pengirim sendiri.
SCOPED_TOOLS = {
    "cek_pesanan", "rekap_omzet", "rekap_harian", "tagihan_belum_bayar",
}
VENDOR_SENDERS = {"warga", "tukang sayur", "bang sayur", "toko", "pemilik"}


def _vendor_ids():
    """ID vendor dari env BANGSAYUR_VENDOR_IDS (dipisah koma, lower/strip).

    Daftar kosong = mode demo: tidak ada ID yang dikenali, _is_vendor
    fallback ke nama pengirim.
    """
    raw = os.environ.get("BANGSAYUR_VENDOR_IDS", "")
    return {v.strip().lower() for v in raw.split(",") if v.strip()}


def _is_vendor(sender, sender_id=None):
    """True kalau pengirim adalah tukang sayur.

    Prioritas: sender_id (ID pengguna, mis. Mattermost user id) yang ada
    di BANGSAYUR_VENDOR_IDS. Kalau daftar ID kosong (mode demo), fallback
    ke nama pengirim di VENDOR_SENDERS — DEMO-ONLY, nama pengirim bisa
    dipalsu siapa pun, JANGAN dipakai di produksi. Kalau daftar ID diset,
    nama saja TIDAK cukup: sender_id harus cocok dengan daftar.
    """
    ids = _vendor_ids()
    if sender_id is not None and str(sender_id).strip():
        if str(sender_id).strip().lower() in ids:
            return True
        if ids:
            # Daftar ID diset dan ID ini tidak dikenal -> bukan vendor,
            # walaupun namanya "Tukang Sayur".
            return False
    if not ids:
        return (sender or "").strip().lower() in VENDOR_SENDERS
    return False


def _nama_norm(nama):
    return (nama or "").strip().lower().replace(" ", "")


def _execute_scoped(name, args, db_path, sender):
    """Versi aman untuk warga non-vendor: hanya data milik pengirim."""
    try:
        if name == "cek_pesanan":
            result = tools_mod.cek_pesanan(args["pesanan_id"], db_path=db_path)
            if not result.get("ok"):
                return result
            if _nama_norm(result.get("nama")) != _nama_norm(sender):
                return {"error": "Pesanan itu bukan milikmu, jadi saya "
                                 "tidak bisa menampilkan detailnya."}
            result = dict(result)
            result["alamat"] = ""
            result.pop("no_hp", None)
            return result
        if name == "rekap_harian":
            return tools_mod.rekap_harian(
                args.get("tanggal") or None, db_path=db_path, nama=sender)
        if name == "tagihan_belum_bayar":
            return tools_mod.tagihan_belum_bayar(db_path=db_path, nama=sender)
        if name == "rekap_omzet":
            return tools_mod.rekap_omzet(
                args.get("mulai"), args.get("sampai"),
                db_path=db_path, nama=sender)
    except (ValueError, KeyError, TypeError) as exc:
        return {"error": str(exc)}
    return {"error": f"Tool '{name}' tidak dikenal."}


def _execute(name, args, db_path, sender=None, sender_id=None):
    # Untuk ubah/batalkan pesanan, kalau model tidak mengirim nama pemilik,
    # isi dari pengirim supaya cek pemilik tetap berlaku untuk warga biasa.
    # Vendor dikecualikan (boleh mengurus pesanan siapa pun).
    if name in ("ubah_pesanan", "batalkan_pesanan") and sender \
            and not _is_vendor(sender, sender_id) and not (args or {}).get("nama"):
        args = dict(args or {})
        args["nama"] = sender
    if name in SCOPED_TOOLS and not _is_vendor(sender, sender_id):
        return _execute_scoped(name, args, db_path, sender)
    if name in VENDOR_TOOLS:
        if not _is_vendor(sender, sender_id):
            return {"error": "Hanya tukang sayur yang bisa melakukan ini. "
                             "Kalau kamu warga, sampaikan ke tukang sayur ya."}
    fn = _TOOL_DISPATCH.get(name)
    if fn is None:
        return {"error": f"Tool '{name}' tidak dikenal."}
    try:
        return fn(args, db_path)
    except (ValueError, KeyError, TypeError) as exc:
        return {"error": str(exc)}


def run_turn(user_message, history=None, db_path=None, max_iterations=4,
             sender=None, sender_id=None):
    """Satu giliran chat: kembalikan {reply, tool_calls, path}.

    sender = nama pengirim ("Bu Sari", "Tukang Sayur", ...). Dipakai
    _execute untuk memblokir tool khusus vendor kalau pengirimnya warga.
    sender_id = ID pengguna (mis. Mattermost user id); kalau diisi dan
    BANGSAYUR_VENDOR_IDS diset, inilah yang menentukan vendor — nama saja
    tidak cukup. Kalau sender kosong, coba baca dari awalan pesan
    "Nama: isi".
    """
    if sender is None:
        m = re.match(r"\s*([^:]{1,40}):\s", user_message or "")
        sender = m.group(1).strip() if m else ""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": user_message})
    executed = []
    path = "direct"
    for _ in range(max_iterations):
        content, tool_calls = _call_model(messages, use_tools=True,
                                          db_path=db_path)
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
                result = _execute(fn["name"], args, db_path, sender=sender,
                                  sender_id=sender_id)
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
                                  db_path, sender=sender,
                                  sender_id=sender_id)
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
    # Iterasi habis tanpa balasan akhir dari model. JANGAN kembalikan
    # messages[-1] — isinya bisa JSON hasil tool, bukan kalimat untuk warga.
    return {"reply": "Maaf, saya belum bisa menyelesaikan permintaan itu. "
                     "Coba ulangi dengan kalimat yang lebih singkat ya.",
            "tool_calls": executed, "path": path}
