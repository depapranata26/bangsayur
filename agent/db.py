#!/usr/bin/env python3
"""BangSayur data layer: SQLite schema + seed data (tukang sayur keliling).

Harga realistis Medan, Nov 2026. Stok = jumlah tersedia hari ini.
Agen TIDAK BOLEH mengarang harga/stok — semua dari tabel ini.
"""
import os
import sqlite3

DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "data", "bangsayur.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY,
    nama TEXT UNIQUE NOT NULL,
    harga INTEGER NOT NULL,
    satuan TEXT NOT NULL,
    stok REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pelanggan (
    id INTEGER PRIMARY KEY,
    nama TEXT NOT NULL,
    blok TEXT NOT NULL,
    alamat TEXT DEFAULT '',
    no_hp TEXT DEFAULT '',
    no_show INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'aktif'
);
CREATE TABLE IF NOT EXISTS pesanan (
    id INTEGER PRIMARY KEY,
    pelanggan_id INTEGER NOT NULL REFERENCES pelanggan(id),
    tanggal TEXT NOT NULL,
    total INTEGER NOT NULL DEFAULT 0,
    status_bayar TEXT NOT NULL DEFAULT 'belum',
    status TEXT NOT NULL DEFAULT 'menunggu_acc',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS pesanan_items (
    id INTEGER PRIMARY KEY,
    pesanan_id INTEGER NOT NULL REFERENCES pesanan(id),
    item_id INTEGER NOT NULL REFERENCES items(id),
    qty REAL NOT NULL,
    harga_satuan INTEGER NOT NULL
);
"""

# (nama, harga Rp, satuan, stok hari ini)
SEED_ITEMS = [
    ("Kangkung", 5000, "ikat", 30),
    ("Bayam", 5000, "ikat", 25),
    ("Sawi hijau", 6000, "ikat", 20),
    ("Daun bawang", 3000, "ikat", 20),
    ("Seledri", 3000, "ikat", 15),
    ("Cabai merah", 48000, "kg", 8),
    ("Cabai rawit", 40000, "kg", 6),
    ("Bawang merah", 36000, "kg", 10),
    ("Bawang putih", 40000, "kg", 8),
    ("Tomat", 16000, "kg", 12),
    ("Wortel", 14000, "kg", 10),
    ("Kentang", 18000, "kg", 12),
    ("Timun", 10000, "kg", 10),
    ("Terong", 12000, "kg", 10),
    ("Kol", 10000, "kg", 8),
    ("Telur ayam", 28000, "kg", 15),
    ("Tempe", 6000, "papan", 20),
    ("Tahu", 5000, "bungkus", 20),
    ("Jahe", 30000, "kg", 4),
    ("Kunyit", 18000, "kg", 4),
]

# (nama, blok, alamat)
SEED_PELANGGAN = [
    ("Bu Sari", "A", "Jl. Melati No. 12"),
    ("Pak Budi", "A", "Jl. Melati No. 5"),
    ("Bu Ratna", "B", "Jl. Kenanga No. 8"),
    ("Pak Agus", "B", "Jl. Kenanga No. 21"),
    ("Bu Dewi", "C", "Jl. Flamboyan No. 3"),
    ("Bu Maya", "C", "Jl. Flamboyan No. 17"),
]

BLOK_RUTE = ["A", "B", "C", "D"]


def connect(db_path=None):
    path = db_path or DEFAULT_DB
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate(conn):
    """Tambah kolom keamanan ke DB lama (tanpa hapus data).

    pesanan.status: menunggu_acc | menunggu_dp | dikonfirmasi | ditolak
        | tidak_diambil. Pesanan lama (sebelum sistem aman) dianggap sudah
        dikonfirmasi agar rekap lama tetap terhitung.
    pelanggan.no_show / pelanggan.status: 'aktif' | 'ditahan'
        (ditahan = 2x tidak ambil pesanan -> wajib DP dulu).
    """
    cols = {r[1] for r in conn.execute("PRAGMA table_info(pelanggan)")}
    if "no_show" not in cols:
        conn.execute("ALTER TABLE pelanggan ADD COLUMN no_show INTEGER NOT NULL DEFAULT 0")
    if "status" not in cols:
        conn.execute("ALTER TABLE pelanggan ADD COLUMN status TEXT NOT NULL DEFAULT 'aktif'")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(pesanan)")}
    if "status" not in cols:
        conn.execute("ALTER TABLE pesanan ADD COLUMN status TEXT NOT NULL DEFAULT 'menunggu_acc'")
        conn.execute("UPDATE pesanan SET status = 'dikonfirmasi' WHERE status = 'menunggu_acc'")
    conn.commit()


def init_db(db_path=None):
    conn = connect(db_path)
    conn.executescript(SCHEMA)
    _migrate(conn)
    n = conn.execute("SELECT COUNT(*) c FROM items").fetchone()["c"]
    if n == 0:
        conn.executemany(
            "INSERT INTO items (nama, harga, satuan, stok) VALUES (?,?,?,?)",
            SEED_ITEMS)
    n = conn.execute("SELECT COUNT(*) c FROM pelanggan").fetchone()["c"]
    if n == 0:
        conn.executemany(
            "INSERT INTO pelanggan (nama, blok, alamat) VALUES (?,?,?)",
            SEED_PELANGGAN)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    conn = connect()
    print("items:", conn.execute("SELECT COUNT(*) c FROM items").fetchone()["c"])
    print("pelanggan:", conn.execute("SELECT COUNT(*) c FROM pelanggan").fetchone()["c"])
    conn.close()
