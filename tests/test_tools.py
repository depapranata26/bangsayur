#!/usr/bin/env python3
"""Tes unit tools BangSayur — unittest stdlib saja (tanpa pytest).

Setiap tes memakai DB SQLite temp sendiri (tempfile.mkdtemp di /tmp);
tidak menyentuh data/ repo. Satu-satunya pengecualian adalah
test_backup_ke_data_repo, yang memang menguji buat_backup() menulis ke
data/ repo — file backup-nya dihapus lagi di cleanup tes itu.

Jalankan dari root repo (/tmp/bangsayur):
    python3 -m unittest discover -s tests -v
"""
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import unittest
from datetime import datetime
from unittest import mock
from zoneinfo import ZoneInfo

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent"),
)

import agent as agent_mod  # noqa: E402
import tools as tools_mod  # noqa: E402


class BangSayurToolsTest(unittest.TestCase):
    """Satu DB temp per tes, di-seed dari db.py (init_db)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="bangsayur-test-")
        self.db = os.path.join(self.tmpdir, "test.db")
        tools_mod.init_db(self.db)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # -- helper ---------------------------------------------------------
    def _stok(self, nama):
        items = tools_mod.daftar_harga(db_path=self.db)["items"]
        return next(i["stok"] for i in items if i["nama"] == nama)

    def _order(self, nama, blok, items):
        r = tools_mod.catat_pesanan(nama, blok, items, db_path=self.db)
        self.assertTrue(r.get("ok"), r)
        return r

    def _order_acc(self, nama, blok, items):
        r = self._order(nama, blok, items)
        acc = tools_mod.konfirmasi_pesanan(
            r["pesanan_id"], "acc", db_path=self.db)
        self.assertTrue(acc.get("ok"), acc)
        return r

    # 1. ACC mengurangi stok tepat sekali; ACC kedua ditolak. -------------
    def test_order_acc_stok_berkurang_sekali(self):
        r = self._order("Bu Sari", "A",
                        [{"nama_item": "Kangkung", "qty": 2}])
        self.assertEqual(r["total"], 10000)
        # Stok belum berkurang sebelum ACC.
        self.assertEqual(self._stok("Kangkung"), 30)
        acc = tools_mod.konfirmasi_pesanan(
            r["pesanan_id"], "acc", db_path=self.db)
        self.assertTrue(acc.get("ok"), acc)
        self.assertEqual(self._stok("Kangkung"), 28)
        # ACC kedua atas pesanan yang sama harus ditolak (tidak dobel).
        acc2 = tools_mod.konfirmasi_pesanan(
            r["pesanan_id"], "acc", db_path=self.db)
        self.assertFalse(acc2.get("ok"))
        self.assertEqual(self._stok("Kangkung"), 28)

    # 2. Privasi: warga hanya melihat pesanannya sendiri. ----------------
    def test_privasi_scoped(self):
        # Bu Sari: 1 kg cabai (48.000) + 2 ikat kangkung (10.000) = 58.000
        o1 = self._order_acc("Bu Sari", "A", [
            {"nama_item": "Cabai merah", "qty": 1},
            {"nama_item": "Kangkung", "qty": 2},
        ])
        self.assertEqual(o1["total"], 58000)
        # Pak Budi: 1 kg telur (28.000) + 2 papan tempe (12.000) = 40.000
        o2 = self._order_acc("Pak Budi", "A", [
            {"nama_item": "Telur ayam", "qty": 1},
            {"nama_item": "Tempe", "qty": 2},
        ])
        self.assertEqual(o2["total"], 40000)
        # Rekap sebagai Bu Ratna: 0 pesanan (bukan miliknya).
        # Pakai tanggal pesanan (bukan "hari ini") supaya tes tetap benar
        # walau dijalankan setelah jam cutoff (pesanan jadi untuk besok).
        rekap = agent_mod._execute(
            "rekap_harian", {"tanggal": o1["tanggal"]}, self.db,
            sender="Bu Ratna")
        self.assertTrue(rekap.get("ok"), rekap)
        self.assertEqual(rekap["jumlah_pesanan"], 0)
        self.assertEqual(rekap["omzet"], 0)
        # cek_pesanan #1 sebagai Bu Ratna: ditolak, bukan miliknya.
        cek_orang = agent_mod._execute(
            "cek_pesanan", {"pesanan_id": o1["pesanan_id"]}, self.db,
            sender="Bu Ratna")
        self.assertIn("error", cek_orang)
        self.assertFalse(cek_orang.get("ok", False))
        # cek_pesanan #1 sebagai pemilik: ok, alamat diredaksi ("").
        cek_milik = agent_mod._execute(
            "cek_pesanan", {"pesanan_id": o1["pesanan_id"]}, self.db,
            sender="Bu Sari")
        self.assertTrue(cek_milik.get("ok"), cek_milik)
        self.assertEqual(cek_milik["alamat"], "")

    # 3. Ubah pesanan orang lain ditolak; pemilik boleh. -----------------
    def test_ubah_pesanan_orang_lain_ditolak(self):
        o1 = self._order("Bu Sari", "A",
                         [{"nama_item": "Kangkung", "qty": 2}])
        o2 = self._order("Pak Budi", "A",
                         [{"nama_item": "Tempe", "qty": 2}])
        baru = [{"nama_item": "Tempe", "qty": 1}]
        # Bu Sari mencoba mengubah pesanan #2 (milik Pak Budi).
        ditolak = agent_mod._execute(
            "ubah_pesanan",
            {"pesanan_id": o2["pesanan_id"], "items": baru},
            self.db, sender="Bu Sari")
        self.assertFalse(ditolak.get("ok", False))
        self.assertIn("error", ditolak)
        # Pemilik sendiri boleh mengubah.
        ok = agent_mod._execute(
            "ubah_pesanan",
            {"pesanan_id": o2["pesanan_id"], "items": baru},
            self.db, sender="Pak Budi")
        self.assertTrue(ok.get("ok"), ok)
        self.assertEqual(ok["total"], 6000)
        # Pesanan Bu Sari tidak ikut berubah.
        cek = tools_mod.cek_pesanan(o1["pesanan_id"], db_path=self.db)
        self.assertEqual(cek["items"][0]["qty"], 2)

    # 4. tambah_catatan menempel (append), bukan menimpa. ----------------
    def test_tambah_catatan_append(self):
        o = self._order("Bu Sari", "A",
                        [{"nama_item": "Kangkung", "qty": 1}])
        pid = o["pesanan_id"]
        r1 = tools_mod.tambah_catatan(pid, "titip ke Bu Sari",
                                      db_path=self.db)
        self.assertTrue(r1.get("ok"), r1)
        self.assertEqual(r1["catatan"], "titip ke Bu Sari")
        r2 = tools_mod.tambah_catatan(pid, "timbangan 1,05 kg",
                                      db_path=self.db)
        self.assertTrue(r2.get("ok"), r2)
        self.assertEqual(r2["catatan"],
                         "titip ke Bu Sari; timbangan 1,05 kg")

    # 5. Pembulatan uang desimal (ROUND_HALF_UP). ------------------------
    def test_kembalian_desimal_tepat(self):
        r1 = tools_mod.hitung_kembalian(4999.5, 10000)
        self.assertTrue(r1.get("ok"), r1)
        self.assertEqual(r1["total"], 5000)
        self.assertEqual(r1["kembalian"], 5000)
        # CATATAN: brief awal menulis kembalian 1500 untuk kasus ini, tapi
        # itu tidak konsisten dengan ROUND_HALF_UP yang dipakai implementasi
        # (dan didokumentasikan di docstring hitung_kembalian: total
        # dibulatkan dulu, baru dikurangi). 58500.5 -> 58501, sehingga
        # 60000 - 58501 = 1499. Nilai 1500 hanya benar kalau yang
        # dibulatkan adalah selisihnya (1499.5 -> 1500) atau dipakai
        # ROUND_HALF_EVEN. Koordinator perlu memutuskan mana yang benar.
        r2 = tools_mod.hitung_kembalian(58500.5, 60000)
        self.assertTrue(r2.get("ok"), r2)
        self.assertEqual(r2["total"], 58501)
        self.assertEqual(r2["kembalian"], 1499)
        # Total order 3333 x 1,5 = 4999.5 dibulatkan jadi 5000 (bukan 4999).
        tools_mod.atur_harga_stok("Kangkung", harga=3333, db_path=self.db)
        o = self._order("Bu Sari", "A",
                        [{"nama_item": "Kangkung", "qty": 1.5}])
        self.assertEqual(o["total"], 5000)

    # 6. Varian parsing alamat untuk urutan rute. ------------------------
    def test_parse_alamat_varian(self):
        kasus = [
            ("Jl. Melati No. 5", ("melati", 5)),
            ("Jalan Kenanga No. 8", ("kenanga", 8)),
            ("Blok A No. 5", ("blok a", 5)),
            ("Gang Melati No. 3", ("melati", 3)),
            ("No. 12", ("", 12)),
            ("", ("", 9999)),
            (None, ("", 9999)),
        ]
        for alamat, harap in kasus:
            with self.subTest(alamat=alamat):
                self.assertEqual(tools_mod._parse_alamat(alamat), harap)

    # 7. Race stok: dua thread tidak boleh oversell cabai (stok 8 kg). ---
    def test_race_stok_dua_thread_tidak_oversell(self):
        barrier = threading.Barrier(2)
        hasil = []  # (nama, catat_ok, acc_ok)
        kunci = threading.Lock()

        def kerja(nama):
            try:
                barrier.wait(timeout=10)
                r = tools_mod.catat_pesanan(
                    nama, "A", [{"nama_item": "Cabai merah", "qty": 5}],
                    db_path=self.db)
                acc_ok = False
                if r.get("ok"):
                    a = tools_mod.konfirmasi_pesanan(
                        r["pesanan_id"], "acc", db_path=self.db)
                    acc_ok = bool(a.get("ok"))
                with kunci:
                    hasil.append((nama, bool(r.get("ok")), acc_ok))
            except Exception:
                # Gagal karena database locked dihitung gagal, bukan sukses.
                with kunci:
                    hasil.append((nama, False, False))

        t1 = threading.Thread(target=kerja, args=("Bu Sari",))
        t2 = threading.Thread(target=kerja, args=("Pak Budi",))
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)
        self.assertFalse(t1.is_alive(), "thread Bu Sari macet")
        self.assertFalse(t2.is_alive(), "thread Pak Budi macet")
        self.assertEqual(len(hasil), 2)
        acc_berhasil = sum(1 for _, _, a in hasil if a)
        self.assertLessEqual(acc_berhasil, 1,
                             f"oversell: {acc_berhasil} ACC berhasil: {hasil}")
        stok_akhir = self._stok("Cabai merah")
        self.assertGreaterEqual(stok_akhir, 0)
        conn = sqlite3.connect(self.db)
        try:
            row = conn.execute(
                "SELECT COALESCE(SUM(pi.qty), 0) q FROM pesanan_items pi "
                "JOIN pesanan p ON p.id = pi.pesanan_id "
                "JOIN items i ON i.id = pi.item_id "
                "WHERE p.status = 'dikonfirmasi' AND i.nama = 'Cabai merah'"
            ).fetchone()
        finally:
            conn.close()
        terkonfirmasi = row[0]
        self.assertLessEqual(terkonfirmasi, 8)
        self.assertEqual(stok_akhir, 8 - terkonfirmasi)

    # 8. run_turn kehabisan iterasi: balasan maaf, bukan JSON. ------------
    def test_run_turn_habis_iterasi_bukan_json(self):
        def _mock_call_model(messages, use_tools=True, max_tokens=1024,
                             db_path=None):
            # Model selalu memanggil tool, tidak pernah memberi balasan akhir.
            return ("", [{"id": "c1", "type": "function",
                          "function": {"name": "daftar_harga",
                                       "arguments": "{}"}}])

        with mock.patch.object(agent_mod, "_call_model",
                               side_effect=_mock_call_model):
            out = agent_mod.run_turn("cek harga dong", db_path=self.db,
                                     max_iterations=2)
        reply = out["reply"]
        self.assertFalse(reply.lstrip().startswith("{"),
                         f"balasan berupa JSON: {reply!r}")
        self.assertIn("Maaf", reply)
        self.assertEqual(len(out["tool_calls"]), 2)

    # 9. Zona waktu WIB. --------------------------------------------------
    def test_wib_asia_jakarta(self):
        self.assertEqual(tools_mod.WIB.key, "Asia/Jakarta")
        self.assertEqual(
            tools_mod._today_wib(),
            datetime.now(ZoneInfo("Asia/Jakarta")).date())

    # 10. Duplikat pelanggan lintas blok (nama tanpa spasi). --------------
    def test_duplikat_pelanggan_lintas_blok(self):
        r = tools_mod.daftar_pelanggan("busari", "B", db_path=self.db)
        self.assertTrue(r.get("ok"), r)
        self.assertTrue(r.get("sudah_ada"))
        self.assertEqual(r.get("nama"), "Bu Sari")
        self.assertEqual(r.get("blok"), "A")

    # 11. ID vendor mengalahkan nama pengirim. ----------------------------
    def test_vendor_id_mengalahkan_nama(self):
        with mock.patch.dict(os.environ,
                             {"BANGSAYUR_VENDOR_IDS": "u-vendor-1"}):
            self.assertFalse(agent_mod._is_vendor(
                "Tukang Sayur", sender_id="orang-lain"))
            self.assertTrue(agent_mod._is_vendor(
                "Bu Sari", sender_id="u-vendor-1"))
        # Tanpa env: mode demo, nama "Tukang Sayur" cukup.
        with mock.patch.dict(os.environ):
            os.environ.pop("BANGSAYUR_VENDOR_IDS", None)
            self.assertTrue(agent_mod._is_vendor("Tukang Sayur"))
            self.assertFalse(agent_mod._is_vendor("Bu Sari"))

    # 12. Backup menulis file data/backup-*.json. -------------------------
    def test_backup_ke_data_repo(self):
        r = tools_mod.buat_backup(db_path=self.db)
        self.assertTrue(r.get("ok"), r)
        self.assertTrue(r["file"].startswith("data/backup-"), r["file"])
        self.assertTrue(os.path.isfile(r["file_abs"]), r["file_abs"])
        # Hapus lagi supaya working tree tetap bersih (bukan file sumber).
        self.addCleanup(_hapus_file, r["file_abs"])


def _hapus_file(path):
    if os.path.exists(path):
        os.remove(path)


if __name__ == "__main__":
    unittest.main()
