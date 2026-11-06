# Transkrip Demo BangSayur — via Webapp (simulasi lokal)

Tanggal: 2026-11-07 (WIB). Room simulasi: webapp lokal (`/api/chat`), BUKAN log live Mattermost/Switch.

## Mode: MOCK (tanpa model)

Transkrip ini dibuat oleh `demo/run_webapp_demo.py --mock`: langkah-langkahnya dijalankan dengan memanggil tool SQLite langsung lewat `agent._execute` (jalur enforcement/privasi yang sama seperti `run_turn`), BUKAN lewat panggilan model Baseten. Balasan agen di bawah ini DISUSUN dari hasil tool — angkanya terverifikasi dari database, tapi teks balasannya rekonstruksi, bukan kutipan balasan model. Jangan klaim ini sebagai log live.

## (a) Bu Sari pesan sayur

> [Bu Sari] halo bang, saya mau pesan 2 ikat kangkung sama 1 kg cabai merah

> [BangSayur] Halo Bu Sari 🥬
>
> • Kangkung 2 ikat - Rp10.000
> • Cabai merah 1 kg - Rp48.000
>
> Total: Rp58.000
>
> Betul? Balas YA.

## (b) Bu Sari balas YA

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

## (c) Vendor ACC pesanan Bu Sari

> [Tukang Sayur] ACC #1

> [BangSayur] Siap! Pesanan #1 Bu Sari sudah di-ACC dan dikonfirmasi 🛵
>
> Total: Rp58.000 | Status bayar: belum

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

## (e) Bu Ratna tanya rekap / tagihan (hanya miliknya)

> [Bu Ratna] bang, rekap hari ini berapa? sama tagihan saya?

> [BangSayur] Halo Bu Ratna 🥬
>
> Rekap hari ini (punya Bu Ratna):
> • Jumlah pesanan: 0
> • Omzet: Rp0
>
> Bu Ratna belum pesan hari ini, jadi belum ada tagihan. 🙏

## (f) Vendor tanya rekap omzet + rute

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
> • Bu Sari A - Rp58.000 (belum)
> • Pak Budi A - Rp40.000 (belum)

> Rute hari ini:
> • Blok A - 2 berhenti
> • Pak Budi - Jl. Melati No. 5 - Rp40.000 - belum
> • Bu Sari - Jl. Melati No. 12 - Rp58.000 - belum
> • Total berhenti: 2
> • Berikutnya: Pak Budi - Jl. Melati No. 5

## Verifikasi DB

Pesanan (SQLite, DB temp skrip):

- #1 Bu Sari: Rp58.000 | status=dikonfirmasi | bayar=belum
- #2 Pak Budi: Rp40.000 | status=dikonfirmasi | bayar=belum

Stok sesudah demo:

- Kangkung: 30 -> 28
- Cabai merah: 8 -> 7
- Telur ayam: 15 -> 14
- Tempe: 20 -> 18

Hasil cek:

- [x] sebelum YA belum ada pesanan tercatat (pesanan=0)
- [x] pesanan Bu Sari total Rp58.000 (Rp58.000)
- [x] pesanan Bu Sari status menunggu_acc (menunggu_acc)
- [x] stok BELUM berkurang sebelum ACC (Kangkung=30, Cabai merah=8)
- [x] pesanan #1 dikonfirmasi setelah ACC (dikonfirmasi)
- [x] stok berkurang SAAT ACC (Kangkung 30->28, Cabai 8->7) (Kangkung=28, Cabai merah=7)
- [x] pesanan Pak Budi total Rp40.000 (Rp40.000)
- [x] pesanan #2 dikonfirmasi setelah ACC (dikonfirmasi)
- [x] stok Telur 15->14, Tempe 20->18 setelah ACC #2 (Telur=14, Tempe=18)
- [x] rekap Bu Ratna hanya miliknya: 0 pesanan, omzet Rp0 (Rp0)
- [x] tagihan Bu Ratna: tidak ada (0) (jumlah=0)
- [x] Bu Ratna tidak bisa cek pesanan Bu Sari ({'error': 'Pesanan itu bukan milikmu, jadi saya tidak bisa menampilkan detailnya)
- [x] omzet vendor Rp98.000 (semua pesanan) (Rp98.000)
- [x] vendor: lunas Rp0, belum Rp98.000 (lunas=Rp0, belum=Rp98.000)
- [x] rute vendor: 2 berhenti, urut No. 5 lalu No. 12 (['Pak Budi', 'Bu Sari'])
- [x] rute berikutnya = Pak Budi (Jl. Melati No. 5) (Jl. Melati No. 5)
- [x] 2 pesanan dikonfirmasi, total Rp98.000 (pesanan=2, total=Rp98.000)
- [x] stok Kangkung 30->28 (stok=28)
- [x] stok Cabai merah 8->7 (stok=7)
- [x] stok Telur ayam 15->14 (stok=14)
- [x] stok Tempe 20->18 (stok=18)
- [x] rekap omzet vendor: Rp98.000, lunas Rp0, belum Rp98.000 (omzet=Rp98.000, lunas=Rp0, belum=Rp98.000)

Semua angka di atas cocok dengan database — agen tidak mengarang harga, total, atau stok. DB temp skrip ada di `/tmp/bangsayur-demo-bu_a251g/webapp-demo.db` (dihapus otomatis bersama /tmp).
