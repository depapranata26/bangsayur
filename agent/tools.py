#!/usr/bin/env python3
"""BangSayur tools: semua operasi data lewat SQLite. Harga & stok HANYA dari DB.

Fungsi-fungsi di sini dipanggil model lewat tool loop (agent.py).
Setiap fungsi mengembalikan dict JSON-able.
"""
from datetime import date, timedelta

from db import BLOK_RUTE, connect, init_db


def _rupiah(n):
    return f"Rp{n:,.0f}".replace(",", ".")


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
    """Cari item berdasarkan nama (case-insensitive, substring)."""
    nama = (nama or "").strip().lower()
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
        "SELECT id, nama, blok, alamat, no_hp FROM pelanggan "
        "WHERE replace(lower(nama), ' ', '') LIKE ? ORDER BY nama",
        ("%" + norm + "%",),
    ).fetchall()
    conn.close()
    return {"ok": True, "ditemukan": len(rows), "pelanggan": [
        {"id": r["id"], "nama": r["nama"], "blok": r["blok"],
         "alamat": r["alamat"], "no_hp": r["no_hp"]} for r in rows]}


def catat_pesanan(nama, blok, items, db_path=None):
    """Catat pesanan baru. items = [{nama_item, qty}]. Harga dari DB, stok dicek.

    Pelanggan baru dibuat otomatis. Stok berkurang. Status bayar = 'belum'.
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
        pel = conn.execute(
            "SELECT id FROM pelanggan WHERE lower(nama) = ? AND blok = ?",
            (nama.lower(), blok)).fetchone()
        if pel:
            pelanggan_id = pel["id"]
        else:
            cur = conn.execute(
                "INSERT INTO pelanggan (nama, blok) VALUES (?, ?)", (nama, blok))
            pelanggan_id = cur.lastrowid
        today = date.today().isoformat()
        cur = conn.execute(
            "INSERT INTO pesanan (pelanggan_id, tanggal, total, status_bayar) "
            "VALUES (?, ?, ?, 'belum')", (pelanggan_id, today, total))
        pesanan_id = cur.lastrowid
        for row, qty in resolved:
            conn.execute(
                "INSERT INTO pesanan_items (pesanan_id, item_id, qty, harga_satuan) "
                "VALUES (?, ?, ?, ?)", (pesanan_id, row["id"], qty, row["harga"]))
            conn.execute("UPDATE items SET stok = stok - ? WHERE id = ?",
                         (qty, row["id"]))
        conn.commit()
        return {"ok": True, "pesanan_id": pesanan_id, "nama": nama,
                "blok": blok, "total": total, "total_rp": _rupiah(total),
                "items": [{"nama": r["nama"], "qty": q,
                           "satuan": r["satuan"],
                           "subtotal_rp": _rupiah(int(r["harga"] * q))}
                          for r, q in resolved],
                "status_bayar": "belum"}
    finally:
        conn.close()


def rekap_harian(tanggal=None, db_path=None):
    """Rekap pesanan hari ini (atau tanggal YYYY-MM-DD): jumlah pesanan,
    total per item, omzet."""
    init_db(db_path)
    tanggal = tanggal or date.today().isoformat()
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT p.id, pl.nama, pl.blok, p.total, p.status_bayar "
        "FROM pesanan p JOIN pelanggan pl ON pl.id = p.pelanggan_id "
        "WHERE p.tanggal = ? ORDER BY p.id", (tanggal,)).fetchall()
    per_item = conn.execute(
        "SELECT i.nama, i.satuan, SUM(pi.qty) qty, "
        "SUM(pi.qty * pi.harga_satuan) subtotal "
        "FROM pesanan_items pi JOIN pesanan p ON p.id = pi.pesanan_id "
        "JOIN items i ON i.id = pi.item_id WHERE p.tanggal = ? "
        "GROUP BY i.id ORDER BY subtotal DESC", (tanggal,)).fetchall()
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
                         for r in per_item]}


def rute_hari_ini(tanggal=None, db_path=None):
    """Rute keliling hari ini: pesanan dikelompokkan per blok,
    urut Blok A → B → C → D."""
    init_db(db_path)
    tanggal = tanggal or date.today().isoformat()
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT p.id, pl.nama, pl.blok, pl.alamat, p.total, p.status_bayar "
        "FROM pesanan p JOIN pelanggan pl ON pl.id = p.pelanggan_id "
        "WHERE p.tanggal = ? ORDER BY p.id", (tanggal,)).fetchall()
    conn.close()
    grouped = {b: [] for b in BLOK_RUTE}
    for r in rows:
        grouped.setdefault(r["blok"], []).append({
            "pesanan_id": r["id"], "nama": r["nama"], "alamat": r["alamat"],
            "total_rp": _rupiah(r["total"]),
            "status_bayar": r["status_bayar"]})
    urutan = [{"blok": b, "berhenti": grouped[b]} for b in BLOK_RUTE
              if grouped[b]]
    return {"ok": True, "tanggal": tanggal, "rute": urutan,
            "total_berhenti": len(rows)}


def tagihan_belum_bayar(db_path=None):
    """Semua pesanan yang status bayarnya masih 'belum' (semua tanggal)."""
    init_db(db_path)
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT p.id, p.tanggal, pl.nama, pl.blok, p.total "
        "FROM pesanan p JOIN pelanggan pl ON pl.id = p.pelanggan_id "
        "WHERE p.status_bayar = 'belum' ORDER BY p.tanggal, p.id"
    ).fetchall()
    conn.close()
    total = sum(r["total"] for r in rows)
    return {"ok": True, "jumlah": len(rows),
            "total_tagihan": total, "total_tagihan_rp": _rupiah(total),
            "tagihan": [{"pesanan_id": r["id"], "tanggal": r["tanggal"],
                         "nama": r["nama"], "blok": r["blok"],
                         "total_rp": _rupiah(r["total"])} for r in rows]}


def tandai_lunas(pesanan_id, db_path=None):
    """Tandai satu pesanan sebagai lunas."""
    init_db(db_path)
    conn = connect(db_path)
    row = conn.execute(
        "SELECT p.id, pl.nama, p.total FROM pesanan p "
        "JOIN pelanggan pl ON pl.id = p.pelanggan_id WHERE p.id = ?",
        (pesanan_id,)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": f"Pesanan #{pesanan_id} tidak ditemukan."}
    conn.execute("UPDATE pesanan SET status_bayar = 'lunas' WHERE id = ?",
                 (pesanan_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "pesanan_id": row["id"], "nama": row["nama"],
            "total_rp": _rupiah(row["total"]), "status_bayar": "lunas"}


def rekap_omzet(mulai=None, sampai=None, db_path=None):
    """Omzet pada rentang tanggal (default: 7 hari terakhir)."""
    init_db(db_path)
    sampai = sampai or date.today().isoformat()
    mulai = mulai or (date.today() - timedelta(days=6)).isoformat()
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT tanggal, COUNT(*) jml, SUM(total) omzet, "
        "SUM(CASE WHEN status_bayar='lunas' THEN total ELSE 0 END) lunas, "
        "SUM(CASE WHEN status_bayar='belum' THEN total ELSE 0 END) belum "
        "FROM pesanan WHERE tanggal BETWEEN ? AND ? GROUP BY tanggal "
        "ORDER BY tanggal", (mulai, sampai)).fetchall()
    conn.close()
    total = sum(r["omzet"] or 0 for r in rows)
    return {"ok": True, "mulai": mulai, "sampai": sampai,
            "total_omzet": total, "total_omzet_rp": _rupiah(total),
            "per_hari": [{"tanggal": r["tanggal"], "pesanan": r["jml"],
                          "omzet_rp": _rupiah(r["omzet"] or 0),
                          "lunas_rp": _rupiah(r["lunas"] or 0),
                          "belum_rp": _rupiah(r["belum"] or 0)}
                         for r in rows]}
