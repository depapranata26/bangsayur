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
        today = date.today().isoformat()
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


def rekap_harian(tanggal=None, db_path=None):
    """Rekap pesanan hari ini (atau tanggal YYYY-MM-DD): jumlah pesanan,
    total per item, omzet. HANYA pesanan 'dikonfirmasi' yang dihitung;
    yang masih menunggu ACC/DP tampil terpisah supaya tukang sayur bisa
    memutuskan."""
    init_db(db_path)
    tanggal = tanggal or date.today().isoformat()
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT p.id, pl.nama, pl.blok, p.total, p.status_bayar "
        "FROM pesanan p JOIN pelanggan pl ON pl.id = p.pelanggan_id "
        "WHERE p.tanggal = ? AND p.status = 'dikonfirmasi' ORDER BY p.id",
        (tanggal,)).fetchall()
    per_item = conn.execute(
        "SELECT i.nama, i.satuan, SUM(pi.qty) qty, "
        "SUM(pi.qty * pi.harga_satuan) subtotal "
        "FROM pesanan_items pi JOIN pesanan p ON p.id = pi.pesanan_id "
        "JOIN items i ON i.id = pi.item_id "
        "WHERE p.tanggal = ? AND p.status = 'dikonfirmasi' "
        "GROUP BY i.id ORDER BY subtotal DESC", (tanggal,)).fetchall()
    menunggu = conn.execute(
        "SELECT p.id, pl.nama, pl.blok, p.total, p.status "
        "FROM pesanan p JOIN pelanggan pl ON pl.id = p.pelanggan_id "
        "WHERE p.tanggal = ? AND p.status IN ('menunggu_acc', 'menunggu_dp') "
        "ORDER BY p.id", (tanggal,)).fetchall()
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
    tanggal = tanggal or date.today().isoformat()
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT p.id, pl.nama, pl.blok, pl.alamat, p.total, p.status_bayar, "
        "p.status_antar "
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
            "status_antar": r["status_antar"]})
    urutan = [{"blok": b, "berhenti": grouped[b]} for b in BLOK_RUTE
              if grouped[b]]
    belum = [r for r in rows if r["status_antar"] == "belum"]
    berikutnya = None
    if belum:
        r = belum[0]
        berikutnya = {"pesanan_id": r["id"], "nama": r["nama"],
                      "blok": r["blok"], "alamat": r["alamat"],
                      "total_rp": _rupiah(r["total"]),
                      "status_bayar": r["status_bayar"]}
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


def tagihan_belum_bayar(db_path=None):
    """Semua pesanan yang status bayarnya masih 'belum' (semua tanggal)."""
    init_db(db_path)
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT p.id, p.tanggal, pl.nama, pl.blok, p.total "
        "FROM pesanan p JOIN pelanggan pl ON pl.id = p.pelanggan_id "
        "WHERE p.status_bayar = 'belum' AND p.status = 'dikonfirmasi' "
        "ORDER BY p.tanggal, p.id"
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
        "FROM pesanan WHERE tanggal BETWEEN ? AND ? "
        "AND status = 'dikonfirmasi' GROUP BY tanggal "
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
