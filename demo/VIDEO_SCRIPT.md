# Naskah Video Demo BangSayur (< 3 menit, direkam dari HP)

Status: **BELUM DIREKAM.** Ikuti naskah ini apa adanya; total durasi
**2 menit 58 detik** (178 detik).

## Yang direkam

Video direkam dari **webapp demo BangSayur di browser HP** (tampilan
chat gaya WA), BUKAN dari Mattermost live — karena jalur live
Switch/Mattermost butuh server yang jalan dan belum dipakai untuk
rekaman ini. Kalau nanti direkam ulang lewat Mattermost live, ganti
Shot 0 dengan layar channel Mattermost dan sebutkan itu di narasi.
Jangan klaim video ini sebagai rekaman live Mattermost.

Alur yang ditunjukkan = alur WAJIB kode sekarang: ringkasan + minta YA
→ setelah YA baru dicatat (menunggu_acc) → vendor ACC → dikonfirmasi,
stok BARU berkurang saat ACC. Privasi scoped: Bu Ratna hanya melihat
miliknya sendiri; rekap omzet + rute hanya untuk vendor.

## Persiapan (sebelum tekan rekam)

1. Jalankan webapp dengan database demo yang bersih (bukan
   `data/webapp.db` produksi), misal:
   `python3 demo/run_webapp_demo.py --live` (server + DB temp di /tmp),
   atau `BANGSAYUR_WEB_PORT=8001 python3 webapp/server.py` lalu buka
   `http://<alamat-server>:8001` di browser HP.
2. HP: mode Jangan Ganggu, matikan notifikasi, kecerahan layar penuh,
   putar HP tegak (portrait). Pakai perekam layar bawaan HP.
3. Siapkan teks pesan di bawah (salin-tempel dari catatan supaya tidak
   salah ketik saat rekaman). Ketik pelan supaya penonton bisa mengikuti.
4. Saat pindah ke pengirim **Tukang Sayur**, aplikasi meminta PIN vendor
   (demo: `1234`) — ketik saat diminta; PIN tidak tampil di layar.
5. Potong jeda loading model ("BangSayur mengetik...") saat edit, tapi
   JANGAN potong isi balasan agen.

## Shot-by-shot

### Shot 0 — Pembuka (0:00–0:10, 10 detik)

- **Layar:** webapp BangSayur (header "BangSayur • online", bubble
  sambutan "Halo! Saya Bang Sayur..."), picker pengirim di kanan atas
  masih "Bu Sari".
- **Narasi:** "Ini BangSayur — agen tukang sayur keliling di grup chat
  warga. Pesan sayur, ACC tukang sayur, sampai rute antar, semua lewat
  chat. Ini demonya."
- **Aksi:** diam 2 detik, lalu scroll sedikit ke atas-bawah supaya
  kelihatan ini aplikasi chat beneran.

### Shot 1 — Bu Sari pesan, agen minta konfirmasi YA (0:10–0:35, 25 detik)

- **Layar:** picker pengirim = **Bu Sari**. Ketik dan kirim:
  "halo bang, saya mau pesan 2 ikat kangkung sama 1 kg cabai merah".
  Balasan agen muncul: ringkasan 2 ikat kangkung Rp10.000 + 1 kg cabai
  merah Rp48.000, total Rp58.000, ditutup "Betul? Balas YA."
- **Narasi:** "Bu Sari pesan 2 ikat kangkung dan 1 kilo cabai merah.
  Agen tidak langsung mencatat — dia ulang dulu ringkasannya dan minta
  konfirmasi."
- **Aksi:** tahan layar 3 detik di balasan ringkasan supaya total
  Rp58.000 terbaca jelas.

### Shot 2 — Bu Sari balas YA, pesanan menunggu ACC (0:35–1:00, 25 detik)

- **Layar:** kirim "YA". Balasan: "Pesanan #1 sudah dicatat ya Bu Sari
  ... Status: menunggu ACC Bang Sayur".
- **Narasi:** "Setelah Bu Sari balas YA, pesanan masuk — tapi statusnya
  masih menunggu ACC. Perhatikan: stok belum berkurang di tahap ini,
  jadi pesanan yang tidak jadi tidak menggerogoti stok."
- **Aksi:** tunjuk (ketuk pelan) baris "menunggu ACC" kalau perlu.

### Shot 3 — Vendor ACC, stok baru berkurang (1:00–1:25, 25 detik)

- **Layar:** ganti picker pengirim ke **Tukang Sayur** (masukkan PIN
  vendor demo `1234` saat diminta). Kirim "ACC #1". Balasan: "Pesanan
  #1 Bu Sari sudah di-ACC dan dikonfirmasi".
- **Narasi:** "Sekarang tukang sayurnya yang ACC. Baru di titik inilah
  pesanan dikonfirmasi — dan stok kangkung berkurang dari 30 jadi 28,
  cabai merah dari 8 jadi 7."
- **Aksi:** kalau sempat, buka sebentar daftar harga (chip "Daftar
  harga") untuk menunjukkan stok sesudah ACC; kalau durasi mepet,
  lewati — cukup sebutkan di narasi.

### Shot 4 — Pak Budi: pesan, YA, ACC (1:25–1:50, 25 detik)

- **Layar:** picker ke **Pak Budi**. Kirim "bang, saya mau 1 kg telur
  ayam sama 2 papan tempe" → ringkasan Rp40.000 → kirim "YA" → pesanan
  #2 menunggu ACC → picker ke **Tukang Sayur**, kirim "ACC #2" →
  dikonfirmasi.
- **Narasi:** "Pak Budi pesan sekilo telur dan dua papan tempe,
  empat puluh ribu. Alurnya sama: ringkasan, YA, lalu ACC tukang
  sayur."
- **Aksi:** percepat dengan memotong jeda ketik (jump cut); yang
  penting keempat bubble balasan kelihatan.

### Shot 5 — Bu Ratna tanya rekap: hanya miliknya sendiri (1:50–2:10, 20 detik)

- **Layar:** picker ke **Bu Ratna**. Kirim "bang, rekap hari ini
  berapa? sama tagihan saya?" Balasan: 0 pesanan, omzet Rp0, belum ada
  tagihan. TIDAK ada nama Bu Sari / Pak Budi di balasan itu.
- **Narasi:** "Bu Ratna belum pesan hari ini. Yang dia lihat cuma
  miliknya sendiri — nol. Pesanan tetangga tidak bocor ke dia."
- **Aksi:** tahan layar 3 detik di balasan rekap Bu Ratna.

### Shot 6 — Vendor tanya rekap omzet: lihat semua (2:10–2:30, 20 detik)

- **Layar:** picker ke **Tukang Sayur**. Kirim "rekap omzet hari ini
  dong". Balasan: 2 pesanan, omzet Rp98.000, lunas Rp0, belum bayar
  Rp98.000, rincian per item + daftar pesanan Bu Sari dan Pak Budi.
- **Narasi:** "Giliran tukang sayur yang tanya: omzet hari ini sembilan
  puluh delapan ribu, dua pesanan, semuanya belum bayar."
- **Aksi:** scroll pelan supaya daftar pesanan terbaca.

### Shot 7 — Vendor tanya rute (2:30–2:50, 20 detik)

- **Layar:** masih sebagai **Tukang Sayur**. Kirim "rute hari ini
  gimana?" Balasan: Blok A, 2 berhenti — Pak Budi Jl. Melati No. 5
  dulu, baru Bu Sari Jl. Melati No. 12; "Berikutnya: Pak Budi".
- **Narasi:** "Rutenya sudah urut supaya tidak bolak-balik: nomor rumah
  kecil dulu. Rute lengkap dengan alamat ini hanya untuk tukang sayur —
  warga biasa tidak bisa memintanya."
- **Aksi:** tahan layar 3 detik di balasan rute.

### Shot 8 — Penutup (2:50–2:58, 8 detik)

- **Layar:** kembali ke tampilan chat (picker Bu Sari).
- **Narasi:** "BangSayur: pesan lewat chat, ACC tukang sayur, stok dan
  omzet tercatat rapi. Terima kasih!"
- **Aksi:** berhenti rekam.

## Total durasi

| Shot | Isi | Durasi |
|------|-----|--------|
| 0 | Pembuka | 10 dtk |
| 1 | Bu Sari pesan + ringkasan | 25 dtk |
| 2 | YA → menunggu ACC | 25 dtk |
| 3 | Vendor ACC → stok berkurang | 25 dtk |
| 4 | Pak Budi pesan + YA + ACC | 25 dtk |
| 5 | Bu Ratna: rekap miliknya saja | 20 dtk |
| 6 | Vendor: rekap omzet Rp98.000 | 20 dtk |
| 7 | Vendor: rute | 20 dtk |
| 8 | Penutup | 8 dtk |
| **Total** | | **178 dtk = 2 mnt 58 dtk** |

## Cek sebelum upload

- [ ] Total Rp58.000 + Rp40.000 = Rp98.000 terbaca di Shot 1, 4, dan 6.
- [ ] Kata "menunggu ACC" kelihatan di Shot 2 sebelum Shot 3.
- [ ] Balasan Bu Ratna (Shot 5) TIDAK menampilkan nama/pesanan orang lain.
- [ ] Rute (Shot 7) urut: Pak Budi No. 5 dulu, baru Bu Sari No. 12.
- [ ] Tidak ada API key, password, atau PIN yang terlihat di layar
      (PIN vendor diketik lewat prompt dan tidak tampil).
- [ ] Judul/deskripsi video menyebut "demo via webapp (simulasi lokal)",
      bukan "rekaman live Mattermost", sampai ada rekaman live beneran.
