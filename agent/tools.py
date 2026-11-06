#!/usr/bin/env python3
"""BangSayur tools: semua operasi data lewat SQLite. Harga & stok HANYA dari DB.

Fungsi-fungsi di sini dipanggil model lewat tool loop (agent.py).
Setiap fungsi mengembalikan dict JSON-able.
"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from db import BLOK_RUTE, connect, init_db

# Semua tanggal "hari ini" / cutoff memakai WIB secara eksplisit, bukan
# waktu lokal server (yang bisa beda zona kalau dijalankan juri di luar).
WIB = ZoneInfo("Asia/Jakarta")


def _today_wib():
    """Tanggal hari ini di WIB, format YYYY-MM-DD."""
    return datetime.now(WIB).date()


def _now_wib():
    """Waktu sekarang di WIB."""
    return datetime.now(WIB)


def _rupiah(n):
    return f"Rp{n:,.0f}".replace(",", ".")


# Singkatan yang dipakai warga sehari-hari (terutama orang tua) -> nama resmi.
# Dicek SEBELUM pencarian substring supaya "bamer" ketemu "Bawang merah".
ALIAS_ITEM = {
    "bamer": "Bawang merah", "baput": "Bawang putih",
    "cabe": "Cabai merah", "cabe merah": "Cabai merah",
    "cabe rawit": "Cabai rawit", "rawit": "Cabai rawit",
    "telur": "Telur ayam", "telor": "Telur ayam",
    "sawi": "Sawi hijau", "kangkung": "Kangkung", "bayam": "Bayam",
    "tomat": "Tomat", "wortel": "Wortel", "kentang": "Kentang",
    "timun": "Timun", "terong": "Terong", "kol": "Kol",
    "tempe": "Tempe", "tahu": "Tahu", "jahe": "Jahe", "kunyit": "Kunyit",
    "daun bawang": "Daun bawang", "bawang daun": "Daun bawang",
    "seledri": "Seledri",
}


def daftar_harga(db_path=None):
    """Daftar semua sayur + harga + stok hari ini."""
    init_db(db_path)
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT id, nama, harga, satuan, stok FROM items ORDER BY nama"
    ).fetchall()
    conn.close()
    return {"ok": True, "items": [
        {"id": r["id"], "nama": r["nama"], "harga": r["harga"],
         "harga_rp": _rupiah(r["harga"]), "satuan": r["satuan"],
         "stok": r["stok"]}
        for r in rows]}


def _cari_item(conn, nama):
    """Cari item berdasarkan nama (case-insensitive, substring).

    Urutan: nama persis -> alias singkatan -> substring. "bamer" harus
    ketemu "Bawang merah" walau hurufnya tidak berurutan.
    """
    nama = (nama or "").strip().lower()
    if nama in ALIAS_ITEM:
        nama = ALIAS_ITEM[nama].lower()
    row = conn.execute(
        "SELECT * FROM items WHERE lower(nama) = ?", (nama,)).fetchone()
    if row:
        return row
    rows = conn.execute(
        "SELECT * FROM items WHERE lower(nama) LIKE ?", ("%" + nama + "%",)
    ).fetchall()
    if len(rows) == 1:
        return rows[0]
    if len(rows) > 1:
        return {"ambiguous": [r["nama"] for r in rows]}
    return None


def atur_harga_stok(nama_item, harga=None, stok=None, db_path=None):
    """Update harga dan/atau stok satu item (habis belanja pasar pagi).
    HANYA untuk tukang sayur."""
    init_db(db_path)
    conn = connect(db_path)
    try:
        row = _cari_item(conn, nama_item)
        if row is None:
            return {"ok": False,
                    "error": f"Sayur '{nama_item}' tidak ada di daftar."}
        if isinstance(row, dict) and row.get("ambiguous"):
            return {"ok": False,
                    "error": f"Nama '{nama_item}' ambigu: "
                             f"{', '.join(row['ambiguous'])}. Sebutkan yang mana."}
        if harga is None and stok is None:
            return {"ok": False, "error": "Tidak ada yang diubah (harga/stok kosong)."}
        if harga is not None:
            if harga <= 0:
                return {"ok": False, "error": "Harga harus lebih dari 0."}
            conn.execute("UPDATE items SET harga = ? WHERE id = ?",
                         (int(harga), row["id"]))
        if stok is not None:
            if stok < 0:
                return {"ok": False, "error": "Stok tidak boleh negatif."}
            conn.execute("UPDATE items SET stok = ? WHERE id = ?",
                         (float(stok), row["id"]))
        conn.commit()
        baru = conn.execute("SELECT * FROM items WHERE id = ?",
                            (row["id"],)).fetchone()
        return {"ok": True, "nama": baru["nama"],
                "harga": baru["harga"], "harga_rp": _rupiah(baru["harga"]),
                "satuan": baru["satuan"], "stok": baru["stok"]}
    finally:
        conn.close()


def cari_pelanggan(nama, db_path=None):
    """Cari pelanggan berdasarkan nama (substring, case-insensitive).

    Dipakai agen SEBELUM tanya blok: kalau pemesan sudah dikenal, pakai
    blok dari database — jangan tanya lagi.
    """
    init_db(db_path)
    conn = connect(db_path)
    # Normalisasi spasi di kedua sisi: username chat "busari" harus ketemu
    # pelanggan "Bu Sari".
    norm = (nama or "").strip().lower().replace(" ", "")
    rows = conn.execute(
        "SELECT id, nama, blok, alamat, no_hp, no_show, status FROM pelanggan "
        "WHERE replace(lower(nama), ' ', '') LIKE ? ORDER BY nama",
        ("%" + norm + "%",),
    ).fetchall()
    conn.close()
    return {"ok": True, "ditemukan": len(rows), "pelanggan": [
        {"id": r["id"], "nama": r["nama"], "blok": r["blok"],
         "alamat": r["alamat"], "no_hp": r["no_hp"],
         "no_show": r["no_show"], "status": r["status"]} for r in rows]}


def daftar_pelanggan(nama, blok, alamat="", db_path=None):
    """Daftarkan pelanggan baru (warga yang belum dikenal).

    Dipakai SEBELUM mencatat pesanan pertama warga baru. Kalau nama sudah
    ada di blok yang sama, kembalikan data yang sudah ada.
    """
    init_db(db_path)
    nama = (nama or "").strip()
    blok = (blok or "").strip().upper()
    if not nama:
        return {"ok": False, "error": "Nama pelanggan wajib diisi."}
    if blok not in BLOK_RUTE:
        return {"ok": False,
                "error": f"Blok tidak dikenal. Blok yang ada: {', '.join(BLOK_RUTE)}."}
    conn = connect(db_path)
    try:
        pel = conn.execute(
            "SELECT id, nama, blok, alamat, no_show, status FROM pelanggan "
            "WHERE lower(nama) = ? AND blok = ?",
            (nama.lower(), blok)).fetchone()
        if pel:
            return {"ok": True, "sudah_ada": True, "id": pel["id"],
                    "nama": pel["nama"], "blok": pel["blok"],
                    "alamat": pel["alamat"], "no_show": pel["no_show"],
                    "status": pel["status"]}
        cur = conn.execute(
            "INSERT INTO pelanggan (nama, blok, alamat) VALUES (?, ?, ?)",
            (nama, blok, alamat or ""))
        conn.commit()
        return {"ok": True, "sudah_ada": False, "id": cur.lastrowid,
                "nama": nama, "blok": blok, "alamat": alamat or "",
                "no_show": 0, "status": "aktif"}
    finally:
        conn.close()


def catat_pesanan(nama, blok, items, db_path=None):
    """Catat pesanan baru sebagai MENUNGGU ACC (belum final).

    Syarat: pelanggan HARUS sudah terdaftar (daftar_pelanggan dulu).
    Pelanggan 'ditahan' (2x tidak ambil pesanan) -> status 'menunggu_dp':
    order hanya jalan setelah tukang sayur konfirmasi DP masuk.
    Stok dicek tapi TIDAK dikurangi di sini — stok baru berkurang saat
    tukang sayur ACC (konfirmasi_pesanan). Jadi order fiktif yang tidak
    pernah di-ACC tidak menggerogoti stok.
    """
    init_db(db_path)
    conn = connect(db_path)
    try:
        nama = (nama or "").strip()
        blok = (blok or "").strip().upper()
        if not nama:
            return {"ok": False, "error": "Nama pelanggan wajib diisi."}
        if blok not in BLOK_RUTE:
            return {"ok": False,
                    "error": f"Blok tidak dikenal. Blok yang ada: {', '.join(BLOK_RUTE)}."}
        if not items:
            return {"ok": False, "error": "Pesanan kosong."}
        pel = conn.execute(
            "SELECT id, nama, blok, no_show, status FROM pelanggan "
            "WHERE lower(nama) = ? AND blok = ?",
            (nama.lower(), blok)).fetchone()
        if not pel:
            return {"ok": False, "error": "PELANGGAN_BELUM_TERDAFTAR",
                    "pesan": f"{nama} belum terdaftar. Daftarkan dulu "
                             "(nama + blok + alamat) sebelum mencatat pesanan."}
        resolved = []
        total = 0
        for it in items:
            row = _cari_item(conn, it.get("nama_item", ""))
            if row is None:
                return {"ok": False,
                        "error": f"Sayur '{it.get('nama_item')}' tidak ada di daftar. "
                                 "Cek daftar_harga dulu."}
            if isinstance(row, dict) and row.get("ambiguous"):
                return {"ok": False,
                        "error": f"Nama '{it.get('nama_item')}' ambigu: "
                                 f"{', '.join(row['ambiguous'])}. Sebutkan yang mana."}
            qty = float(it.get("qty") or 0)
            if qty <= 0:
                return {"ok": False,
                        "error": f"Jumlah '{row['nama']}' harus lebih dari 0."}
            if qty > row["stok"]:
                return {"ok": False,
                        "error": f"Stok {row['nama']} tinggal {row['stok']} {row['satuan']}, "
                                 f"tidak cukup untuk {qty} {row['satuan']}."}
            resolved.append((row, qty))
            total += int(row["harga"] * qty)
        status = "menunggu_dp" if pel["status"] == "ditahan" else "menunggu_acc"
        if _pengaturan(conn, "status_toko", "buka") == "libur":
            pesan = _pengaturan(conn, "pesan_libur", "")
            return {"ok": False, "error": "TOKO_LIBUR",
                    "pesan": pesan or "Hari ini Bang Sayur libur."}
        today, besok = _tanggal_order(conn)
        cur = conn.execute(
            "INSERT INTO pesanan (pelanggan_id, tanggal, total, status_bayar, status) "
            "VALUES (?, ?, ?, 'belum', ?)", (pel["id"], today, total, status))
        pesanan_id = cur.lastrowid
        for row, qty in resolved:
            conn.execute(
                "INSERT INTO pesanan_items (pesanan_id, item_id, qty, harga_satuan) "
                "VALUES (?, ?, ?, ?)", (pesanan_id, row["id"], qty, row["harga"]))
        conn.commit()
        return {"ok": True, "pesanan_id": pesanan_id, "nama": pel["nama"],
                "blok": blok, "total": total, "total_rp": _rupiah(total),
                "tanggal": today, "untuk_besok": besok,
                "items": [{"nama": r["nama"], "qty": q,
                           "satuan": r["satuan"],
                           "subtotal_rp": _rupiah(int(r["harga"] * q))}
                          for r, q in resolved],
                "status": status, "status_bayar": "belum",
                "no_show_pelanggan": pel["no_show"]}
    finally:
        conn.close()


def konfirmasi_pesanan(pesanan_id, aksi, db_path=None):
    """Keputusan tukang sayur atas satu pesanan. HANYA untuk tukang sayur.

    aksi:
    - 'acc': menunggu_acc -> dikonfirmasi. Stok dicek ulang lalu dikurangi.
    - 'tolak': menunggu_acc/menunggu_dp -> ditolak (stok tidak berubah).
    - 'dp_masuk': menunggu_dp -> menunggu_acc (DP sudah diterima).
    """
    init_db(db_path)
    aksi = (aksi or "").strip().lower()
    if aksi not in ("acc", "tolak", "dp_masuk"):
        return {"ok": False, "error": "Aksi harus: acc, tolak, atau dp_masuk."}
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT p.id, p.status, p.total, pl.nama FROM pesanan p "
            "JOIN pelanggan pl ON pl.id = p.pelanggan_id WHERE p.id = ?",
            (pesanan_id,)).fetchone()
        if not row:
            return {"ok": False, "error": f"Pesanan #{pesanan_id} tidak ditemukan."}
        status = row["status"]
        if aksi == "acc":
            if status != "menunggu_acc":
                return {"ok": False,
                        "error": f"Pesanan #{pesanan_id} statusnya '{status}', "
                                 "tidak bisa di-ACC."}
            items = conn.execute(
                "SELECT pi.qty, i.id, i.nama, i.stok, i.satuan "
                "FROM pesanan_items pi JOIN items i ON i.id = pi.item_id "
                "WHERE pi.pesanan_id = ?", (pesanan_id,)).fetchall()
            for it in items:
                if it["qty"] > it["stok"]:
                    return {"ok": False,
                            "error": f"Stok {it['nama']} tinggal {it['stok']} "
                                     f"{it['satuan']}, tidak cukup untuk pesanan ini."}
            for it in items:
                conn.execute("UPDATE items SET stok = stok - ? WHERE id = ?",
                             (it["qty"], it["id"]))
            conn.execute("UPDATE pesanan SET status = 'dikonfirmasi' WHERE id = ?",
                         (pesanan_id,))
            conn.commit()
            return {"ok": True, "pesanan_id": pesanan_id, "nama": row["nama"],
                    "total_rp": _rupiah(row["total"]), "status": "dikonfirmasi"}
        if aksi == "tolak":
            if status not in ("menunggu_acc", "menunggu_dp"):
                return {"ok": False,
                        "error": f"Pesanan #{pesanan_id} statusnya '{status}', "
                                 "tidak bisa ditolak."}
            conn.execute("UPDATE pesanan SET status = 'ditolak' WHERE id = ?",
                         (pesanan_id,))
            conn.commit()
            return {"ok": True, "pesanan_id": pesanan_id, "nama": row["nama"],
                    "total_rp": _rupiah(row["total"]), "status": "ditolak"}
        # dp_masuk
        if status != "menunggu_dp":
            return {"ok": False,
                    "error": f"Pesanan #{pesanan_id} statusnya '{status}', "
                             "bukan menunggu DP."}
        conn.execute("UPDATE pesanan SET status = 'menunggu_acc' WHERE id = ?",
                     (pesanan_id,))
        conn.commit()
        return {"ok": True, "pesanan_id": pesanan_id, "nama": row["nama"],
                "total_rp": _rupiah(row["total"]), "status": "menunggu_acc"}
    finally:
        conn.close()


def tandai_tidak_diambil(pesanan_id, db_path=None):
    """Tukang sayur sudah sampai tapi warga tidak mengambil pesanan.

    Stok dikembalikan, pesanan jadi 'tidak_diambil', no_show pelanggan +1.
    no_show >= 2 -> pelanggan 'ditahan' (order berikutnya wajib DP dulu).
    HANYA untuk tukang sayur.
    """
    init_db(db_path)
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT p.id, p.status, p.total, pl.id AS pel_id, pl.nama, "
            "pl.no_show FROM pesanan p "
            "JOIN pelanggan pl ON pl.id = p.pelanggan_id WHERE p.id = ?",
            (pesanan_id,)).fetchone()
        if not row:
            return {"ok": False, "error": f"Pesanan #{pesanan_id} tidak ditemukan."}
        if row["status"] != "dikonfirmasi":
            return {"ok": False,
                    "error": f"Pesanan #{pesanan_id} statusnya '{row['status']}', "
                             "hanya pesanan dikonfirmasi yang bisa ditandai tidak diambil."}
        items = conn.execute(
            "SELECT pi.qty, i.id FROM pesanan_items pi "
            "JOIN items i ON i.id = pi.item_id WHERE pi.pesanan_id = ?",
            (pesanan_id,)).fetchall()
        for it in items:
            conn.execute("UPDATE items SET stok = stok + ? WHERE id = ?",
                         (it["qty"], it["id"]))
        conn.execute("UPDATE pesanan SET status = 'tidak_diambil' WHERE id = ?",
                     (pesanan_id,))
        no_show = (row["no_show"] or 0) + 1
        status = "ditahan" if no_show >= 2 else "aktif"
        conn.execute("UPDATE pelanggan SET no_show = ?, status = ? WHERE id = ?",
                     (no_show, status, row["pel_id"]))
        conn.commit()
        return {"ok": True, "pesanan_id": pesanan_id, "nama": row["nama"],
                "total_rp": _rupiah(row["total"]), "status": "tidak_diambil",
                "no_show": no_show, "status_pelanggan": status}
    finally:
        conn.close()


def daftar_menunggu_acc(db_path=None):
    """Daftar pesanan yang menunggu keputusan tukang sayur (ACC / DP / tolak)."""
    init_db(db_path)
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT p.id, p.tanggal, p.total, p.status, pl.nama, pl.blok "
        "FROM pesanan p JOIN pelanggan pl ON pl.id = p.pelanggan_id "
        "WHERE p.status IN ('menunggu_acc', 'menunggu_dp') "
        "ORDER BY p.id"
    ).fetchall()
    conn.close()
    return {"ok": True, "jumlah": len(rows),
            "menunggu": [{"pesanan_id": r["id"], "tanggal": r["tanggal"],
                          "nama": r["nama"], "blok": r["blok"],
                          "total_rp": _rupiah(r["total"]),
                          "status": r["status"]} for r in rows]}


def cek_pesanan(pesanan_id, db_path=None):
    """Detail satu pesanan: status, pelanggan, item, total, status bayar."""
    init_db(db_path)
    conn = connect(db_path)
    row = conn.execute(
        "SELECT p.id, p.tanggal, p.total, p.status, p.status_bayar, "
        "pl.nama, pl.blok, pl.alamat FROM pesanan p "
        "JOIN pelanggan pl ON pl.id = p.pelanggan_id WHERE p.id = ?",
        (pesanan_id,)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": f"Pesanan #{pesanan_id} tidak ditemukan."}
    items = conn.execute(
        "SELECT i.nama, pi.qty, i.satuan, pi.harga_satuan "
        "FROM pesanan_items pi JOIN items i ON i.id = pi.item_id "
        "WHERE pi.pesanan_id = ?", (pesanan_id,)).fetchall()
    conn.close()
    return {"ok": True, "pesanan_id": row["id"], "tanggal": row["tanggal"],
            "nama": row["nama"], "blok": row["blok"], "alamat": row["alamat"],
            "total_rp": _rupiah(row["total"]), "status": row["status"],
            "status_bayar": row["status_bayar"],
            "items": [{"nama": i["nama"], "qty": i["qty"],
                       "satuan": i["satuan"],
                       "subtotal_rp": _rupiah(int(i["harga_satuan"] * i["qty"]))}
                      for i in items]}


def ubah_pesanan(pesanan_id, items, db_path=None, nama=None):
    """Ganti isi pesanan yang masih menunggu ACC (warga salah ketik / berubah
    pikiran). Total dihitung ulang dari DB, stok dicek ulang. Setelah ACC
    tidak bisa diubah lagi — harus hubungi tukang sayur.
    Kalau `nama` diisi, harus cocok dengan pemilik pesanan (seperti
    batalkan_pesanan), supaya warga lain tidak bisa mengubah pesanan orang."""
    init_db(db_path)
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT p.id, p.status, pl.nama FROM pesanan p "
            "JOIN pelanggan pl ON pl.id = p.pelanggan_id WHERE p.id = ?",
            (pesanan_id,)).fetchone()
        if not row:
            return {"ok": False, "error": f"Pesanan #{pesanan_id} tidak ditemukan."}
        if nama and _nama_norm(row["nama"]) != _nama_norm(nama):
            return {"ok": False,
                    "error": f"Pesanan #{pesanan_id} itu milik {row['nama']}, "
                             "bukan milikmu."}
        if row["status"] not in ("menunggu_acc", "menunggu_dp"):
            return {"ok": False,
                    "error": f"Pesanan #{pesanan_id} statusnya '{row['status']}', "
                             "sudah tidak bisa diubah."}
        if not items:
            return {"ok": False, "error": "Pesanan pengganti kosong."}
        resolved = []
        total = 0
        for it in items:
            item = _cari_item(conn, it.get("nama_item", ""))
            if item is None:
                return {"ok": False,
                        "error": f"Sayur '{it.get('nama_item')}' tidak ada di daftar."}
            if isinstance(item, dict) and item.get("ambiguous"):
                return {"ok": False,
                        "error": f"Nama '{it.get('nama_item')}' ambigu: "
                                 f"{', '.join(item['ambiguous'])}."}
            qty = float(it.get("qty") or 0)
            if qty <= 0:
                return {"ok": False, "error": "Jumlah harus lebih dari 0."}
            if qty > item["stok"]:
                return {"ok": False,
                        "error": f"Stok {item['nama']} tinggal {item['stok']} "
                                 f"{item['satuan']}."}
            resolved.append((item, qty))
            total += int(item["harga"] * qty)
        conn.execute("DELETE FROM pesanan_items WHERE pesanan_id = ?",
                     (pesanan_id,))
        for item, qty in resolved:
            conn.execute(
                "INSERT INTO pesanan_items (pesanan_id, item_id, qty, harga_satuan) "
                "VALUES (?, ?, ?, ?)", (pesanan_id, item["id"], qty, item["harga"]))
        conn.execute("UPDATE pesanan SET total = ? WHERE id = ?",
                     (total, pesanan_id))
        conn.commit()
        return {"ok": True, "pesanan_id": pesanan_id, "nama": row["nama"],
                "total": total, "total_rp": _rupiah(total),
                "status": row["status"],
                "items": [{"nama": r["nama"], "qty": q, "satuan": r["satuan"],
                           "subtotal_rp": _rupiah(int(r["harga"] * q))}
                          for r, q in resolved]}
    finally:
        conn.close()


def batalkan_pesanan(pesanan_id, nama=None, db_path=None):
    """Warga membatalkan pesanannya sendiri yang masih menunggu ACC/DP.
    Kalau nama diisi, harus cocok dengan pemilik pesanan (biar warga lain
    tidak bisa membatalkan pesanan orang)."""
    init_db(db_path)
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT p.id, p.status, pl.nama FROM pesanan p "
            "JOIN pelanggan pl ON pl.id = p.pelanggan_id WHERE p.id = ?",
            (pesanan_id,)).fetchone()
        if not row:
            return {"ok": False, "error": f"Pesanan #{pesanan_id} tidak ditemukan."}
        if nama and row["nama"].lower() != (nama or "").strip().lower():
            return {"ok": False,
                    "error": f"Pesanan #{pesanan_id} itu milik {row['nama']}, "
                             "bukan milikmu."}
        if row["status"] not in ("menunggu_acc", "menunggu_dp"):
            return {"ok": False,
                    "error": f"Pesanan #{pesanan_id} statusnya '{row['status']}', "
                             "sudah tidak bisa dibatalkan dari sini."}
        conn.execute("UPDATE pesanan SET status = 'ditolak' WHERE id = ?",
                     (pesanan_id,))
        conn.commit()
        return {"ok": True, "pesanan_id": pesanan_id, "nama": row["nama"],
                "status": "ditolak"}
    finally:
        conn.close()


def catat_komplain(nama, isi, pesanan_id=None, db_path=None):
    """Catat keluhan warga (sayur layu, timbangan kurang, salah kirim).
    Disimpan supaya tukang sayur bisa menindaklanjuti."""
    init_db(db_path)
    isi = (isi or "").strip()
    if not isi:
        return {"ok": False, "error": "Isi keluhan kosong."}
    conn = connect(db_path)
    try:
        pel = conn.execute(
            "SELECT id, nama FROM pelanggan WHERE lower(nama) = ?",
            ((nama or "").strip().lower(),)).fetchone()
        cur = conn.execute(
            "INSERT INTO komplain (pesanan_id, pelanggan_id, isi, tanggal) "
            "VALUES (?, ?, ?, ?)",
            (pesanan_id, pel["id"] if pel else None, isi,
             _today_wib().isoformat()))
        conn.commit()
        return {"ok": True, "komplain_id": cur.lastrowid,
                "nama": pel["nama"] if pel else (nama or "").strip(),
                "isi": isi}
    finally:
        conn.close()


def daftar_komplain(status=None, db_path=None):
    """Daftar keluhan (untuk tukang sayur). Default: yang masih 'baru'."""
    init_db(db_path)
    conn = connect(db_path)
    if status:
        rows = conn.execute(
            "SELECT k.id, k.tanggal, k.isi, k.status, k.pesanan_id, "
            "pl.nama FROM komplain k LEFT JOIN pelanggan pl "
            "ON pl.id = k.pelanggan_id WHERE k.status = ? ORDER BY k.id",
            (status,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT k.id, k.tanggal, k.isi, k.status, k.pesanan_id, "
            "pl.nama FROM komplain k LEFT JOIN pelanggan pl "
            "ON pl.id = k.pelanggan_id ORDER BY k.id"
        ).fetchall()
    conn.close()
    return {"ok": True, "jumlah": len(rows),
            "komplain": [{"id": r["id"], "tanggal": r["tanggal"],
                          "nama": r["nama"], "pesanan_id": r["pesanan_id"],
                          "isi": r["isi"], "status": r["status"]}
                         for r in rows]}


def _nama_norm(nama):
    """Normalisasi nama untuk pencocokan: huruf kecil, tanpa spasi."""
    return (nama or "").strip().lower().replace(" ", "")


def rekap_harian(tanggal=None, db_path=None, nama=None):
    """Rekap pesanan hari ini (atau tanggal YYYY-MM-DD): jumlah pesanan,
    total per item, omzet. HANYA pesanan 'dikonfirmasi' yang dihitung;
    yang masih menunggu ACC/DP tampil terpisah supaya tukang sayur bisa
    memutuskan. Kalau `nama` diisi, hanya pesanan milik nama itu yang
    dihitung (dipakai untuk warga non-vendor)."""
    init_db(db_path)
    tanggal = tanggal or _today_wib().isoformat()
    conn = connect(db_path)
    extra = ""
    params_extra = ()
    if nama:
        extra = (" AND replace(lower(pl.nama), ' ', '') = ?")
        params_extra = (_nama_norm(nama),)
    rows = conn.execute(
        "SELECT p.id, pl.nama, pl.blok, p.total, p.status_bayar "
        "FROM pesanan p JOIN pelanggan pl ON pl.id = p.pelanggan_id "
        "WHERE p.tanggal = ? AND p.status = 'dikonfirmasi'" + extra +
        " ORDER BY p.id",
        (tanggal,) + params_extra).fetchall()
    per_item = conn.execute(
        "SELECT i.nama, i.satuan, SUM(pi.qty) qty, "
        "SUM(pi.qty * pi.harga_satuan) subtotal "
        "FROM pesanan_items pi JOIN pesanan p ON p.id = pi.pesanan_id "
        "JOIN pelanggan pl ON pl.id = p.pelanggan_id "
        "JOIN items i ON i.id = pi.item_id "
        "WHERE p.tanggal = ? AND p.status = 'dikonfirmasi'" + extra +
        " GROUP BY i.id ORDER BY subtotal DESC",
        (tanggal,) + params_extra).fetchall()
    menunggu = conn.execute(
        "SELECT p.id, pl.nama, pl.blok, p.total, p.status "
        "FROM pesanan p JOIN pelanggan pl ON pl.id = p.pelanggan_id "
        "WHERE p.tanggal = ? AND p.status IN ('menunggu_acc', 'menunggu_dp')"
        + extra + " ORDER BY p.id",
        (tanggal,) + params_extra).fetchall()
    conn.close()
    omzet = sum(r["total"] for r in rows)
    return {"ok": True, "tanggal": tanggal,
            "jumlah_pesanan": len(rows),
            "omzet": omzet, "omzet_rp": _rupiah(omzet),
            "pesanan": [{"id": r["id"], "nama": r["nama"], "blok": r["blok"],
                         "total_rp": _rupiah(r["total"]),
                         "status_bayar": r["status_bayar"]} for r in rows],
            "per_item": [{"nama": r["nama"], "qty": r["qty"],
                          "satuan": r["satuan"],
                          "subtotal_rp": _rupiah(int(r["subtotal"] or 0))}
                         for r in per_item],
            "menunggu": [{"pesanan_id": r["id"], "nama": r["nama"],
                          "blok": r["blok"], "total_rp": _rupiah(r["total"]),
                          "status": r["status"]} for r in menunggu]}


def rute_hari_ini(tanggal=None, db_path=None):
    """Rute keliling hari ini: pesanan dikonfirmasi, diurutkan supaya tukang
    sayur tidak bolak-balik — Blok A → B → C → D, di dalam blok diurutkan
    per jalan lalu nomor rumah ("Jl. Melati No. 5" sebelum "No. 12").

    Tiap berhenti membawa status_antar ('belum'/'diantar'). Balasan juga
    membawa 'berikutnya': berhenti terdekat yang belum diantar.
    """
    init_db(db_path)
    tanggal = tanggal or _today_wib().isoformat()
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT p.id, pl.nama, pl.blok, pl.alamat, p.total, p.status_bayar, "
        "p.status_antar, p.catatan "
        "FROM pesanan p JOIN pelanggan pl ON pl.id = p.pelanggan_id "
        "WHERE p.tanggal = ? AND p.status = 'dikonfirmasi' ORDER BY p.id",
        (tanggal,)).fetchall()
    conn.close()

    def _kunci(r):
        blok_i = BLOK_RUTE.index(r["blok"]) if r["blok"] in BLOK_RUTE else 99
        jalan, nomor = _parse_alamat(r["alamat"])
        return (blok_i, jalan, nomor)

    rows = sorted(rows, key=_kunci)
    grouped = {b: [] for b in BLOK_RUTE}
    for r in rows:
        grouped.setdefault(r["blok"], []).append({
            "pesanan_id": r["id"], "nama": r["nama"], "alamat": r["alamat"],
            "total_rp": _rupiah(r["total"]),
            "status_bayar": r["status_bayar"],
            "status_antar": r["status_antar"],
            "catatan": r["catatan"] or ""})
    urutan = [{"blok": b, "berhenti": grouped[b]} for b in BLOK_RUTE
              if grouped[b]]
    belum = [r for r in rows if r["status_antar"] == "belum"]
    berikutnya = None
    if belum:
        r = belum[0]
        berikutnya = {"pesanan_id": r["id"], "nama": r["nama"],
                      "blok": r["blok"], "alamat": r["alamat"],
                      "total_rp": _rupiah(r["total"]),
                      "status_bayar": r["status_bayar"],
                      "catatan": r["catatan"] or ""}
    return {"ok": True, "tanggal": tanggal, "rute": urutan,
            "total_berhenti": len(rows),
            "sudah_diantar": len(rows) - len(belum),
            "belum_diantar": len(belum),
            "berikutnya": berikutnya}


def tandai_diantar(pesanan_id, db_path=None):
    """Tandai satu berhenti sudah diantar (tukang sayur sudah sampai di
    rumah warga). HANYA untuk tukang sayur, hanya pesanan dikonfirmasi."""
    init_db(db_path)
    conn = connect(db_path)
    row = conn.execute(
        "SELECT p.id, p.status, p.status_antar, pl.nama, p.total "
        "FROM pesanan p JOIN pelanggan pl ON pl.id = p.pelanggan_id "
        "WHERE p.id = ?", (pesanan_id,)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": f"Pesanan #{pesanan_id} tidak ditemukan."}
    if row["status"] != "dikonfirmasi":
        conn.close()
        return {"ok": False,
                "error": f"Pesanan #{pesanan_id} statusnya '{row['status']}', "
                         "hanya pesanan dikonfirmasi yang bisa ditandai diantar."}
    if row["status_antar"] == "diantar":
        conn.close()
        return {"ok": False,
                "error": f"Pesanan #{pesanan_id} sudah ditandai diantar."}
    conn.execute("UPDATE pesanan SET status_antar = 'diantar' WHERE id = ?",
                 (pesanan_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "pesanan_id": pesanan_id, "nama": row["nama"],
            "total_rp": _rupiah(row["total"]), "status_antar": "diantar"}


def rute_berikutnya(db_path=None):
    """Berhenti berikutnya hari ini yang belum diantar (urut rute)."""
    init_db(db_path)
    r = rute_hari_ini(db_path=db_path)
    if not r["ok"]:
        return r
    if r["berikutnya"] is None:
        return {"ok": True, "selesai": True,
                "pesan": "Semua berhenti hari ini sudah diantar."}
    return {"ok": True, "selesai": False, "berikutnya": r["berikutnya"],
            "sisa_berhenti": r["belum_diantar"],
            "total_berhenti": r["total_berhenti"]}


def _parse_alamat(alamat):
    """"Jl. Melati No. 12" -> ("melati", 12). Dipakai mengurutkan berhenti
    di dalam satu blok supaya tidak bolak-balik."""
    import re
    m = re.search(r"(?:jl\.?|jalan)\s+([a-zA-Z\s]+?)\s*(?:no\.?|nomor)?\s*(\d+)",
                  alamat or "", re.IGNORECASE)
    if m:
        return (m.group(1).strip().lower(), int(m.group(2)))
    angka = re.findall(r"\d+", alamat or "")
    return ((alamat or "").lower(), int(angka[-1]) if angka else 9999)


def tagihan_belum_bayar(db_path=None, nama=None):
    """Semua pesanan yang status bayarnya masih 'belum' (semua tanggal).
    Kalau `nama` diisi, hanya tagihan milik nama itu (warga non-vendor)."""
    init_db(db_path)
    conn = connect(db_path)
    extra = ""
    params = ()
    if nama:
        extra = " AND replace(lower(pl.nama), ' ', '') = ?"
        params = (_nama_norm(nama),)
    rows = conn.execute(
        "SELECT p.id, p.tanggal, pl.nama, pl.blok, p.total, p.status_bayar, "
        "p.metode_bayar, p.lapor_bayar, p.jatuh_tempo "
        "FROM pesanan p JOIN pelanggan pl ON pl.id = p.pelanggan_id "
        "WHERE p.status_bayar IN ('belum', 'bon') "
        "AND p.status = 'dikonfirmasi'" + extra +
        " ORDER BY p.tanggal, p.id",
        params
    ).fetchall()
    conn.close()
    total = sum(r["total"] for r in rows)
    return {"ok": True, "jumlah": len(rows),
            "total_tagihan": total, "total_tagihan_rp": _rupiah(total),
            "tagihan": [{"pesanan_id": r["id"], "tanggal": r["tanggal"],
                         "nama": r["nama"], "blok": r["blok"],
                         "total_rp": _rupiah(r["total"]),
                         "status_bayar": r["status_bayar"],
                         "metode_bayar": r["metode_bayar"] or "-",
                         "lapor_bayar": r["lapor_bayar"] or "-",
                         "jatuh_tempo": r["jatuh_tempo"] or "-"}
                        for r in rows]}


def tandai_lunas(pesanan_id, metode=None, db_path=None):
    """Tandai satu pesanan sebagai lunas. metode: tunai / transfer / qris
    (opsional, dicatat supaya ketahuan uangnya lewat mana)."""
    init_db(db_path)
    conn = connect(db_path)
    row = conn.execute(
        "SELECT p.id, p.status, pl.nama, p.total FROM pesanan p "
        "JOIN pelanggan pl ON pl.id = p.pelanggan_id WHERE p.id = ?",
        (pesanan_id,)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": f"Pesanan #{pesanan_id} tidak ditemukan."}
    if row["status"] != "dikonfirmasi":
        conn.close()
        return {"ok": False,
                "error": f"Pesanan #{pesanan_id} statusnya '{row['status']}', "
                         "hanya pesanan dikonfirmasi yang bisa ditandai lunas."}
    metode = (metode or "").strip().lower()
    if metode and metode not in ("tunai", "transfer", "qris"):
        conn.close()
        return {"ok": False,
                "error": "Metode harus: tunai, transfer, atau qris."}
    conn.execute("UPDATE pesanan SET status_bayar = 'lunas', metode_bayar = ? "
                 "WHERE id = ?", (metode, pesanan_id))
    conn.commit()
    conn.close()
    return {"ok": True, "pesanan_id": row["id"], "nama": row["nama"],
            "total_rp": _rupiah(row["total"]), "status_bayar": "lunas",
            "metode_bayar": metode or "-"}


def tandai_bon(pesanan_id, jatuh_tempo=None, db_path=None):
    """Pesanan dibon (bayar nanti, mis. akhir minggu). status_bayar jadi
    'bon', tetap masuk tagihan sampai dilunasi."""
    init_db(db_path)
    conn = connect(db_path)
    row = conn.execute(
        "SELECT p.id, p.status, pl.nama, p.total FROM pesanan p "
        "JOIN pelanggan pl ON pl.id = p.pelanggan_id WHERE p.id = ?",
        (pesanan_id,)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": f"Pesanan #{pesanan_id} tidak ditemukan."}
    if row["status"] != "dikonfirmasi":
        conn.close()
        return {"ok": False,
                "error": f"Pesanan #{pesanan_id} statusnya '{row['status']}', "
                         "hanya pesanan dikonfirmasi yang bisa dibon."}
    conn.execute("UPDATE pesanan SET status_bayar = 'bon', "
                 "metode_bayar = 'bon', jatuh_tempo = ? WHERE id = ?",
                 ((jatuh_tempo or "").strip(), pesanan_id))
    conn.commit()
    conn.close()
    return {"ok": True, "pesanan_id": row["id"], "nama": row["nama"],
            "total_rp": _rupiah(row["total"]), "status_bayar": "bon",
            "jatuh_tempo": (jatuh_tempo or "").strip() or "-"}


def hitung_kembalian(total, uang_bayar, db_path=None):
    """Hitung kembalian tunai: total tagihan vs uang yang dikasih warga."""
    try:
        total = int(total)
        uang_bayar = int(uang_bayar)
    except (TypeError, ValueError):
        return {"ok": False, "error": "Total dan uang bayar harus angka."}
    if uang_bayar < total:
        return {"ok": False, "kurang_rp": _rupiah(total - uang_bayar),
                "error": f"Uang kurang {_rupiah(total - uang_bayar)}."}
    return {"ok": True, "total_rp": _rupiah(total),
            "uang_bayar_rp": _rupiah(uang_bayar),
            "kembalian_rp": _rupiah(uang_bayar - total)}


def lapor_bayar(pesanan_id, metode, db_path=None):
    """Warga melapor sudah bayar (biasanya transfer/QRIS + bukti).
    Pesanan ditandai 'lapor bayar' supaya tukang sayur verifikasi dan
    menandai lunas — pembayaran TIDAK otomatis lunas sebelum diverifikasi."""
    init_db(db_path)
    metode = (metode or "").strip().lower()
    if metode not in ("transfer", "qris", "tunai"):
        return {"ok": False,
                "error": "Metode harus: transfer, qris, atau tunai."}
    conn = connect(db_path)
    row = conn.execute(
        "SELECT p.id, p.status, p.status_bayar, pl.nama, p.total "
        "FROM pesanan p JOIN pelanggan pl ON pl.id = p.pelanggan_id "
        "WHERE p.id = ?", (pesanan_id,)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": f"Pesanan #{pesanan_id} tidak ditemukan."}
    if row["status"] != "dikonfirmasi":
        conn.close()
        return {"ok": False,
                "error": f"Pesanan #{pesanan_id} statusnya '{row['status']}'."}
    if row["status_bayar"] != "belum":
        conn.close()
        return {"ok": False,
                "error": f"Pesanan #{pesanan_id} sudah {row['status_bayar']}."}
    conn.execute("UPDATE pesanan SET lapor_bayar = ? WHERE id = ?",
                 (metode, pesanan_id))
    conn.commit()
    conn.close()
    return {"ok": True, "pesanan_id": pesanan_id, "nama": row["nama"],
            "total_rp": _rupiah(row["total"]), "lapor_bayar": metode}


def tambah_catatan(pesanan_id, catatan, db_path=None):
    """Tambah catatan ke pesanan, mis. 'titip ke Bu Sari' atau
    'timbangan 1,05 kg'. Catatan tampil di rute supaya tukang sayur ingat.
    Catatan baru DITAMBAHKAN ke catatan lama (dipisah '; '), bukan menimpa."""
    init_db(db_path)
    catatan = (catatan or "").strip()
    if not catatan:
        return {"ok": False, "error": "Catatan kosong."}
    conn = connect(db_path)
    row = conn.execute(
        "SELECT p.id, p.status, pl.nama, p.catatan FROM pesanan p "
        "JOIN pelanggan pl ON pl.id = p.pelanggan_id WHERE p.id = ?",
        (pesanan_id,)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": f"Pesanan #{pesanan_id} tidak ditemukan."}
    lama = (row["catatan"] or "").strip()
    gabung = f"{lama}; {catatan}" if lama else catatan
    conn.execute("UPDATE pesanan SET catatan = ? WHERE id = ?",
                 (gabung, pesanan_id))
    conn.commit()
    conn.close()
    return {"ok": True, "pesanan_id": pesanan_id, "nama": row["nama"],
            "catatan": gabung}


# ---- toko: libur & batas order ----

def _pengaturan(conn, kunci, default=""):
    row = conn.execute("SELECT nilai FROM pengaturan WHERE kunci = ?",
                       (kunci,)).fetchone()
    return row["nilai"] if row else default


def _set_pengaturan(conn, kunci, nilai):
    conn.execute("INSERT INTO pengaturan (kunci, nilai) VALUES (?, ?) "
                 "ON CONFLICT(kunci) DO UPDATE SET nilai = excluded.nilai",
                 (kunci, nilai))
    conn.commit()


def cek_status_toko(db_path=None):
    """Status toko hari ini: buka/libur + pesan + jam batas order (cutoff)."""
    init_db(db_path)
    conn = connect(db_path)
    status = _pengaturan(conn, "status_toko", "buka")
    pesan = _pengaturan(conn, "pesan_libur", "")
    cutoff = _pengaturan(conn, "jam_cutoff", "07:00")
    conn.close()
    return {"ok": True, "status_toko": status, "pesan": pesan,
            "jam_cutoff": cutoff}


def atur_status_toko(status, pesan="", db_path=None):
    """Tukang sayur mengumumkan libur/sakit (atau buka lagi).
    status: 'buka' atau 'libur'. Kalau libur, agen menolak pesanan baru
    dan menyampaikan pesan ini ke warga."""
    init_db(db_path)
    status = (status or "").strip().lower()
    if status not in ("buka", "libur"):
        return {"ok": False, "error": "Status harus: buka atau libur."}
    conn = connect(db_path)
    _set_pengaturan(conn, "status_toko", status)
    _set_pengaturan(conn, "pesan_libur", (pesan or "").strip())
    conn.close()
    return {"ok": True, "status_toko": status, "pesan": (pesan or "").strip()}


def atur_cutoff(jam, db_path=None):
    """Atur jam batas order (format HH:MM, mis. 07:00). Pesanan setelah jam
    ini otomatis jadi pesanan besok."""
    init_db(db_path)
    import re
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", (jam or "").strip()):
        return {"ok": False, "error": "Jam harus format HH:MM, mis. 07:00."}
    conn = connect(db_path)
    _set_pengaturan(conn, "jam_cutoff", (jam or "").strip())
    conn.close()
    return {"ok": True, "jam_cutoff": (jam or "").strip()}


def _tanggal_order(conn):
    """Tanggal pesanan: hari ini, kecuali sudah lewat jam cutoff -> besok."""
    from datetime import timedelta
    cutoff = _pengaturan(conn, "jam_cutoff", "07:00")
    try:
        hh, mm = (int(x) for x in cutoff.split(":"))
    except ValueError:
        hh, mm = 7, 0
    now = _now_wib()
    if (now.hour, now.minute) >= (hh, mm):
        return (now + timedelta(days=1)).date().isoformat(), True
    return now.date().isoformat(), False


def rekap_omzet(mulai=None, sampai=None, db_path=None, nama=None):
    """Omzet pada rentang tanggal (default: 7 hari terakhir).
    Kalau `nama` diisi, hanya omzet milik nama itu (warga non-vendor)."""
    init_db(db_path)
    sampai = sampai or _today_wib().isoformat()
    mulai = mulai or (_today_wib() - timedelta(days=6)).isoformat()
    conn = connect(db_path)
    extra = ""
    params = (mulai, sampai)
    if nama:
        extra = (" AND replace(lower(pl.nama), ' ', '') = ?")
        params = (mulai, sampai, _nama_norm(nama))
    rows = conn.execute(
        "SELECT p.tanggal, COUNT(*) jml, SUM(p.total) omzet, "
        "SUM(CASE WHEN p.status_bayar='lunas' THEN p.total ELSE 0 END) lunas, "
        "SUM(CASE WHEN p.status_bayar='belum' THEN p.total ELSE 0 END) belum, "
        "SUM(CASE WHEN p.status_bayar='bon' THEN p.total ELSE 0 END) bon "
        "FROM pesanan p JOIN pelanggan pl ON pl.id = p.pelanggan_id "
        "WHERE p.tanggal BETWEEN ? AND ? "
        "AND p.status = 'dikonfirmasi'" + extra + " GROUP BY p.tanggal "
        "ORDER BY p.tanggal", params).fetchall()
    conn.close()
    total = sum(r["omzet"] or 0 for r in rows)
    return {"ok": True, "mulai": mulai, "sampai": sampai,
            "total_omzet": total, "total_omzet_rp": _rupiah(total),
            "per_hari": [{"tanggal": r["tanggal"], "pesanan": r["jml"],
                          "omzet_rp": _rupiah(r["omzet"] or 0),
                          "lunas_rp": _rupiah(r["lunas"] or 0),
                          "belum_rp": _rupiah(r["belum"] or 0),
                          "bon_rp": _rupiah(r["bon"] or 0)}
                         for r in rows]}


# ---- backup & biaya AI ----

def buat_backup(db_path=None):
    """Salin seluruh isi database ke file JSON (data/backup-YYYYMMDD-HHMMSS.json).
    Dipakai tukang sayur sebelum ganti HP / tiap akhir minggu, supaya
    pesanan + tagihan tidak hilang kalau DB rusak."""
    import json
    init_db(db_path)
    conn = connect(db_path)
    try:
        data = {}
        for tabel in ("items", "pelanggan", "pesanan", "pesanan_items",
                      "komplain", "pengaturan", "biaya"):
            rows = conn.execute(f"SELECT * FROM {tabel}").fetchall()
            data[tabel] = [dict(r) for r in rows]
    finally:
        conn.close()
    import os
    folder = os.path.join(os.path.dirname(os.path.abspath(db_path or "")),
                          "..", "data") if db_path else "data"
    folder = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    os.makedirs(folder, exist_ok=True)
    nama = f"backup-{_now_wib().strftime('%Y%m%d-%H%M%S')}.json"
    path = os.path.join(folder, nama)
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return {"ok": True, "file": path,
            "pesanan": len(data["pesanan"]),
            "pelanggan": len(data["pelanggan"]),
            "komplain": len(data["komplain"])}


def catat_pemakaian(token_masuk, token_keluar, db_path=None):
    """Catat token satu panggilan model (dipanggil agent.py tiap balasan).
    Best-effort: gagal catat tidak boleh merusak balasan."""
    try:
        init_db(db_path)
        conn = connect(db_path)
        conn.execute(
            "INSERT INTO biaya (tanggal, token_masuk, token_keluar) "
            "VALUES (?, ?, ?)",
            (_today_wib().isoformat(), int(token_masuk or 0), int(token_keluar or 0)))
        conn.commit()
        conn.close()
        return {"ok": True}
    except Exception:
        return {"ok": False}


def cek_biaya(tanggal=None, db_path=None):
    """Pemakaian AI: jumlah panggilan + total token hari ini (atau tanggal
    tertentu). Harga Rupiah tidak ditampilkan karena tarif Baseten berubah —
    yang dicatat tokennya."""
    init_db(db_path)
    tanggal = tanggal or _today_wib().isoformat()
    conn = connect(db_path)
    row = conn.execute(
        "SELECT COUNT(*) jml, COALESCE(SUM(token_masuk), 0) masuk, "
        "COALESCE(SUM(token_keluar), 0) keluar FROM biaya WHERE tanggal = ?",
        (tanggal,)).fetchone()
    conn.close()
    return {"ok": True, "tanggal": tanggal, "panggilan": row["jml"],
            "token_masuk": row["masuk"], "token_keluar": row["keluar"],
            "total_token": row["masuk"] + row["keluar"]}
