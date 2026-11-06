#!/usr/bin/env python3
"""Tes dashboard vendor BangSayur — unittest stdlib saja (tanpa pytest).

Menguji pemisahan warga vs vendor: chat warga di / tidak berisi urusan
vendor, dan semua endpoint /api/vendor/* PIN-gated. Server HTTP asli
dijalankan di port acak dengan DB SQLite temp sendiri; tidak menyentuh
data/ repo dan tidak memanggil model (endpoint vendor memanggil
tools.py langsung, bukan lewat LLM).

Jalankan dari root repo:
    python3 -m unittest discover -s tests -v
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "agent"))
sys.path.insert(0, os.path.join(REPO_ROOT, "webapp"))

import tools as tools_mod  # noqa: E402
import server as server_mod  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402

VENDOR_PIN = "9999"  # PIN vendor untuk tes ini (diset di server_mod).


class VendorDashboardTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="bangsayur-vendor-")
        self.db = os.path.join(self.tmpdir, "test.db")
        tools_mod.init_db(self.db)
        # Pesanan #1 Bu Sari masih menunggu ACC; #2 Pak Budi sudah ACC.
        r1 = tools_mod.catat_pesanan(
            "Bu Sari", "A",
            [{"nama_item": "Kangkung", "qty": 2},
             {"nama_item": "Cabai merah", "qty": 1}], db_path=self.db)
        self.assertTrue(r1.get("ok"), r1)
        self.order_menunggu = r1["pesanan_id"]
        r2 = tools_mod.catat_pesanan(
            "Pak Budi", "A", [{"nama_item": "Telur ayam", "qty": 1}],
            db_path=self.db)
        self.assertTrue(r2.get("ok"), r2)
        self.order_acc = r2["pesanan_id"]
        acc = tools_mod.konfirmasi_pesanan(
            self.order_acc, "acc", db_path=self.db)
        self.assertTrue(acc.get("ok"), acc)

        server_mod.WEBAPP_DB = self.db
        server_mod.VENDOR_PIN = VENDOR_PIN
        self.httpd = ThreadingHTTPServer(
            ("127.0.0.1", 0), server_mod.Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever,
                                       daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # -- helper HTTP ------------------------------------------------------
    def _url(self, path, pin=None):
        base = f"http://127.0.0.1:{self.port}{path}"
        if pin is not None:
            base += ("&" if "?" in base else "?") + f"pin={pin}"
        return base

    def _call(self, method, path, body=None, pin=None):
        data = (json.dumps(body).encode("utf-8")
                if body is not None else None)
        req = urllib.request.Request(
            self._url(path, pin), data=data, method=method,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def _get(self, path, pin=None):
        return self._call("GET", path, pin=pin)

    def _post(self, path, body, pin=None):
        return self._call("POST", path, body=body, pin=pin)

    def _stok(self, nama):
        items = tools_mod.daftar_harga(db_path=self.db)["items"]
        return next(i["stok"] for i in items if i["nama"] == nama)

    def _harga(self, nama):
        items = tools_mod.daftar_harga(db_path=self.db)["items"]
        return next(i["harga"] for i in items if i["nama"] == nama)

    # -- PIN gate ---------------------------------------------------------
    def test_ringakasan_tanpa_pin_403_tanpa_data(self):
        status, body = self._get("/api/vendor/ringkasan")
        self.assertEqual(status, 403)
        self.assertNotIn("Bu Sari", json.dumps(body, ensure_ascii=False))
        self.assertNotIn("Rp58", json.dumps(body, ensure_ascii=False))

    def test_ringakasan_pin_salah_403(self):
        status, _body = self._get("/api/vendor/ringkasan", pin="0000")
        self.assertEqual(status, 403)

    def test_ringakasan_pin_benar(self):
        status, body = self._get("/api/vendor/ringkasan", pin=VENDOR_PIN)
        self.assertEqual(status, 200, body)
        self.assertEqual(len(body["menunggu"]["menunggu"]), 1)
        # Rekap hanya hitung yang dikonfirmasi (Pak Budi Rp28.000).
        self.assertEqual(body["rekap"]["omzet"], 28000)
        self.assertEqual(len(body["tagihan"]["tagihan"]), 1)

    def test_menunggu_endpoint_tanpa_pin_403(self):
        status, _body = self._get("/api/vendor/menunggu")
        self.assertEqual(status, 403)
        status, body = self._get("/api/vendor/menunggu", pin=VENDOR_PIN)
        self.assertEqual(status, 200)
        self.assertEqual(body["jumlah"], 1)

    # -- ACC / diantar / lunas via endpoint -------------------------------
    def test_acc_tanpa_pin_tidak_mengurangi_stok(self):
        status, _body = self._post(
            "/api/vendor/acc",
            {"pesanan_id": self.order_menunggu, "aksi": "acc"})
        self.assertEqual(status, 403)
        self.assertEqual(self._stok("Kangkung"), 30)

    def test_acc_via_endpoint_mengurangi_stok_sekali(self):
        status, body = self._post(
            "/api/vendor/acc",
            {"pesanan_id": self.order_menunggu, "aksi": "acc"},
            pin=VENDOR_PIN)
        self.assertEqual(status, 200)
        self.assertTrue(body.get("ok"), body)
        self.assertEqual(self._stok("Kangkung"), 28)
        status, body = self._post(
            "/api/vendor/acc",
            {"pesanan_id": self.order_menunggu, "aksi": "acc"},
            pin=VENDOR_PIN)
        self.assertFalse(body.get("ok"))
        self.assertEqual(self._stok("Kangkung"), 28)

    def test_diantar_hanya_untuk_pesanan_dikonfirmasi(self):
        status, body = self._post(
            "/api/vendor/diantar",
            {"pesanan_id": self.order_menunggu}, pin=VENDOR_PIN)
        self.assertFalse(body.get("ok"))
        status, body = self._post(
            "/api/vendor/diantar",
            {"pesanan_id": self.order_acc}, pin=VENDOR_PIN)
        self.assertTrue(body.get("ok"), body)

    def test_lunas_via_endpoint(self):
        status, body = self._post(
            "/api/vendor/lunas",
            {"pesanan_id": self.order_acc, "metode": "tunai"},
            pin=VENDOR_PIN)
        self.assertTrue(body.get("ok"), body)
        _s, tagihan = self._get("/api/vendor/ringkasan", pin=VENDOR_PIN)
        self.assertEqual(tagihan["tagihan"]["jumlah"], 0)

    # -- harga & status toko hanya via vendor ----------------------------
    def test_harga_tanpa_pin_tidak_berubah(self):
        status, _body = self._post(
            "/api/vendor/harga",
            {"nama_item": "Kangkung", "harga": 99999})
        self.assertEqual(status, 403)
        self.assertEqual(self._harga("Kangkung"), 5000)

    def test_harga_dengan_pin_berubah(self):
        status, body = self._post(
            "/api/vendor/harga",
            {"nama_item": "Kangkung", "harga": 6000}, pin=VENDOR_PIN)
        self.assertTrue(body.get("ok"), body)
        self.assertEqual(self._harga("Kangkung"), 6000)

    def test_status_toko_via_endpoint(self):
        status, body = self._post(
            "/api/vendor/status",
            {"status": "libur", "pesan": "Sakit, libur hari ini"},
            pin=VENDOR_PIN)
        self.assertTrue(body.get("ok"), body)
        self.assertEqual(
            tools_mod.cek_status_toko(db_path=self.db)["status_toko"],
            "libur")
        _s, body = self._post(
            "/api/vendor/status", {"status": "buka", "pesan": ""},
            pin=VENDOR_PIN)
        self.assertTrue(body.get("ok"), body)

    # -- pemisahan tampilan warga vs vendor -------------------------------
    def test_chat_warga_tanpa_urusan_vendor(self):
        with open(os.path.join(REPO_ROOT, "webapp", "index.html"),
                  encoding="utf-8") as f:
            html = f.read()
        for chip_vendor in ("Total hari ini", "Rute hari ini",
                            "Rekap omzet", "Menunggu ACC"):
            self.assertNotIn(chip_vendor, html)
        for chip_warga in ("Pesan sayur", "Daftar harga", "Pesanan saya",
                           "Tagihan saya"):
            self.assertIn(chip_warga, html)
        self.assertIn("Dashboard Tukang Sayur", html)
        self.assertIn("/vendor", html)
        # Picker warga tidak berisi opsi Tukang Sayur.
        self.assertNotIn("opts.push('Tukang Sayur')", html)

    def test_dashboard_vendor_pin_gated_tanpa_pin_di_html(self):
        with open(os.path.join(REPO_ROOT, "webapp", "vendor.html"),
                  encoding="utf-8") as f:
            html = f.read()
        self.assertNotIn("1234", html)
        self.assertIn("PIN vendor", html)
        for bagian in ("Menunggu ACC", "Rekap hari ini",
                       "Tagihan belum bayar", "Rute hari ini",
                       "Harga &amp; stok", "Komplain", "Status toko"):
            self.assertIn(bagian, html)


if __name__ == "__main__":
    unittest.main()
