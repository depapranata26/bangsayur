# Transkrip Demo BangSayur (terverifikasi via simulasi lokal)

Room simulasi: **Warung Sayur - Komplek Melati** (skenario demo, bukan
channel Mattermost live)
Tanggal: 2026-11-07 (WIB). Agen: BangSayur (Muse Spark via Baseten).

> **JUJUR SOAL STATUS:** transkrip ini **BUKAN** log live Mattermost /
> Switch. Transkrip ini diverifikasi via simulasi lokal dengan
> `demo/run_webapp_demo.py --mock`: tiap langkah dijalankan dengan
> memanggil tool SQLite langsung lewat `agent._execute` (jalur
> enforcement/privasi yang sama seperti `run_turn`), dan angkanya dicek
> langsung dari database. Balasan agen di bawah ini disusun dari hasil
> tool mengikuti gaya balasan agen — teksnya rekonstruksi, bukan kutipan
> balasan model live. Hasil run lengkap (termasuk 22 cek yang lolos) ada
> di `demo/transcript-webapp.md`.
>
> Alur yang ditunjukkan di sini adalah alur WAJIB kode sekarang:
> cari_pelanggan dulu → ringkasan + minta YA → setelah YA baru
> `catat_pesanan` (status **menunggu_acc**) → vendor ACC
> (`konfirmasi_pesanan acc`) → **dikonfirmasi**, dan stok **BARU**
> berkurang saat ACC. Privasi scoped: warga biasa hanya melihat
> pesanannya sendiri; vendor melihat semua; rute lengkap hanya untuk
> vendor. Di Mattermost akun vendor bernama `warga`; di simulasi ini
> pengirimnya ditulis `Tukang Sayur` (keduanya dikenali sebagai vendor
> oleh agen).

## (a) Bu Sari pesan sayur — ringkasan dulu, belum dicatat

> [Bu Sari] halo bang, saya mau pesan 2 ikat kangkung sama 1 kg cabai merah

> [BangSayur] Halo Bu Sari 🥬
>
> • Kangkung 2 ikat - Rp10.000
> • Cabai merah 1 kg - Rp48.000
>
> Total: Rp58.000
>
> Betul? Balas YA.

## (b) Bu Sari balas YA — pesanan masuk, menunggu ACC

> [Bu Sari] YA

> [BangSayur] Pesanan #1 sudah dicatat ya Bu Sari 🥬
>
> • Kangkung 2 ikat - Rp10.000
> • Cabai merah 1 kg - Rp48.000
>
> Total: Rp58.000
> Status: menunggu ACC Bang Sayur
>
> Nanti Bang Sayur mampir ke Blok A ya Bu. Makasih 🙏

Stok saat ini BELUM berkurang: Kangkung masih 30, Cabai merah masih 8.

## (c) Vendor ACC pesanan Bu Sari — baru sekarang stok berkurang

> [Tukang Sayur] ACC #1

> [BangSayur] Siap! Pesanan #1 Bu Sari sudah di-ACC dan dikonfirmasi 🛵
>
> Total: Rp58.000 | Status bayar: belum

Stok sesudah ACC: Kangkung 30 -> 28, Cabai merah 8 -> 7.

## (d) Pak Budi pesan, YA, lalu ACC

> [Pak Budi] bang, saya mau 1 kg telur ayam sama 2 papan tempe

> [BangSayur] Halo Pak Budi 🥬
>
> • Telur ayam 1 kg - Rp28.000
> • Tempe 2 papan - Rp12.000
>
> Total: Rp40.000
>
> Betul? Balas YA.

> [Pak Budi] YA

> [BangSayur] Pesanan #2 sudah dicatat ya Pak Budi 🥬
>
> • Telur ayam 1 kg - Rp28.000
> • Tempe 2 papan - Rp12.000
>
> Total: Rp40.000
> Status: menunggu ACC Bang Sayur

> [Tukang Sayur] ACC #2

> [BangSayur] Siap! Pesanan #2 Pak Budi sudah di-ACC dan dikonfirmasi 🛵
>
> Total: Rp40.000 | Status bayar: belum

Stok sesudah ACC: Telur ayam 15 -> 14, Tempe 20 -> 18.
Total dikonfirmasi sejauh ini: Rp58.000 + Rp40.000 = **Rp98.000**.

## (e) Bu Ratna tanya rekap / tagihan — hanya miliknya sendiri

> [Bu Ratna] bang, rekap hari ini berapa? sama tagihan saya?

> [BangSayur] Halo Bu Ratna 🥬
>
> Rekap hari ini (punya Bu Ratna):
> • Jumlah pesanan: 0
> • Omzet: Rp0
>
> Bu Ratna belum pesan hari ini, jadi belum ada tagihan. 🙏

Bu Ratna belum pesan apa-apa, jadi rekap/tagihannya 0. Dia TIDAK melihat
pesanan Bu Sari / Pak Budi — rekap warga biasa difilter ke miliknya
sendiri. (Kalau dia coba cek pesanan orang lain, agen menolak: "Pesanan
itu bukan milikmu, jadi saya tidak bisa menampilkan detailnya.")

## (f) Vendor tanya rekap omzet — lihat semua

> [Tukang Sayur] rekap omzet hari ini dong, sama rute

> [BangSayur] Siap, ini rekap omzet 2026-11-07 🥬
>
> • Jumlah pesanan: 2
> • Omzet: Rp98.000
> • Lunas: Rp0
> • Belum bayar: Rp98.000
>
> Rincian per item:
> • Cabai merah 1 kg - Rp48.000
> • Telur ayam 1 kg - Rp28.000
> • Tempe 2 papan - Rp12.000
> • Kangkung 2 ikat - Rp10.000
>
> Daftar pesanan:
> • Bu Sari Blok A - Rp58.000 (belum)
> • Pak Budi Blok A - Rp40.000 (belum)

## (g) Rute keliling — hanya untuk vendor

> [BangSayur] Rute hari ini:
> • Blok A - 2 berhenti
> • Pak Budi - Jl. Melati No. 5 - Rp40.000 - belum
> • Bu Sari - Jl. Melati No. 12 - Rp58.000 - belum
> • Total berhenti: 2
> • Berikutnya: Pak Budi - Jl. Melati No. 5

Rute sudah urut supaya tidak bolak-balik: di jalan yang sama, nomor
rumah kecil dulu (No. 5 sebelum No. 12). Rute lengkap dengan alamat
HANYA untuk tukang sayur — warga biasa tidak bisa memintanya.

## Verifikasi database (SQLite, DB temp skrip mock)

```
pesanan: #1 Bu Sari Rp58.000 dikonfirmasi/belum
         #2 Pak Budi Rp40.000 dikonfirmasi/belum
stok sesudah demo: Kangkung 30 -> 28, Cabai merah 8 -> 7,
                   Telur ayam 15 -> 14, Tempe 20 -> 18
omzet (dikonfirmasi): Rp98.000 | lunas Rp0 | belum Rp98.000
```

Semua angka di jawaban agen cocok dengan database — agen tidak mengarang
harga, total, atau stok. Perintah verifikasi ulang:

```
python3 demo/run_webapp_demo.py --mock
```

(22 cek: total, status menunggu_acc -> dikonfirmasi, stok hanya
berkurang saat ACC, rekap scoped Bu Ratna = 0, omzet vendor Rp98.000,
urutan rute No. 5 lalu No. 12.)
