# BangSayur — Agen Tukang Sayur Keliling di Grup Chat

**Flip the Switch Hackathon** (WeMakeDevs × DevTools Academy × Switch) —
Track 01: Best Business Workflow. Submit tutup **8 Nov 2026 01:29 WIB**.

Warga komplek pesan sayur di grup chat, dan **BangSayur** — agen AI yang hidup
di grup itu lewat [Switch](https://github.com/sandbox-quantum/switch) —
mencatat pesanan, merangkum total harian, mengatur rute per blok, menagih yang
belum bayar, dan merekap omzet. Bukan chatbot yang cuma jawab teks: tiap
jawaban berasal dari database (SQLite) lewat tool calls, jadi harga, total,
dan stok tidak pernah dikarang.

Otak agen: **Muse Spark** (`meta-models/muse-spark-open-1026`) via Baseten
(OpenAI-compatible endpoint). Bahasa: Indonesia.

## Yang sudah terbukti jalan (live, 5 Nov 2026)

Skenario demo lengkap di room Mattermost **Warung Sayur - Komplek Melati**,
transkrip penuh di [`demo/transcript-demo.md`](demo/transcript-demo.md)
(versi Inggris dengan terjemahan:
[`demo/transcript-demo-EN.md`](demo/transcript-demo-EN.md)):

| # | Warga | Agen | Hasil |
|---|-------|------|-------|
| a | Bu Sari pesan 2 ikat kangkung + 1 kg cabai merah | `cari_pelanggan` → `catat_pesanan` | Pesanan #1, Rp58.000, stok berkurang |
| a | Pak Budi pesan 1 kg telur + 2 papan tempe | `catat_pesanan` | Pesanan #2, Rp40.000 |
| b | "total pesanan hari ini berapa?" | `rekap_harian` | 2 pesanan, omzet Rp98.000 |
| c | "rute hari ini gimana?" | `rute_hari_ini` | Blok A, 2 berhenti, urut alamat |
| d | "siapa aja yang belum bayar?" | `tagihan_belum_bayar` | 2 orang, total Rp98.000 |
| e | "rekap omzet hari ini dong" | `rekap_omzet` | Omzet Rp98.000, lunas Rp0 |

## Arsitektur

```
Warga (Mattermost, room #pesan-sayur) ──bridge──> Switch Core ──SSE──> agent/run.py (BANGSAYUR_ROLE=warga)
Tukang sayur (Mattermost, room #dapur-bangsayur) ──bridge──> Switch Core ──SSE──> agent/run.py (BANGSAYUR_ROLE=vendor)
                                                                                  │
                                                                     Muse Spark (Baseten)
                                                                                  │ tool calls
                                                                            SQLite (data/*.db)
```

**Dua room, bukan satu chat.** Tukang sayur TIDAK bekerja di chat warga:
warga pesan di `#pesan-sayur` dan hanya melihat pesanannya sendiri,
sementara tukang sayur ACC pesanan, membaca rekap, menyusun rute, dan
menagih di `#dapur-bangsayur` (khusus vendor). Pesanan baru dari room
warga muncul di room vendor sebagai "menunggu ACC"; tukang sayur ACC di
sana, lalu agen memberi tahu warga di room warga bahwa pesanannya
dikonfirmasi. Satu koneksi Switch hanya bisa claim satu room, jadi dua
room dilayani dua proses runner yang berbagi DB dan kredensial agen
yang sama (lihat langkah 4 di bawah).
**Status: desain dua room dan kode pendukungnya sudah ada, tapi BELUM
PERNAH DITES LIVE di Switch/Mattermost** — jangan klaim demo dua room
live sebelum dijalankan dan dibuktikan.

- **Switch Core** — server Switch (open source), jalan di `http://127.0.0.1:8000`.
  Room di-bridge ke channel Mattermost bawaan Switch.
- **`agent/run.py`** — runner: buka SSE stream, heartbeat 5 dtk, `connect_to_room`,
  dengarkan pesan yang mention `@bangsayur`, jalankan tool loop, balas via
  `post_message`.
- **`agent/agent.py`** — otak: tool loop Muse Spark (native `tool_calls` +
  fallback blok ```json), persona Bang Sayur, aturan keras "harga/stok hanya
  dari tools".
- **`agent/tools.py` + `agent/db.py`** — 7 tools di SQLite: `cari_pelanggan`,
  `daftar_harga`, `catat_pesanan`, `rekap_harian`, `rute_hari_ini`,
  `tagihan_belum_bayar`, `tandai_lunas`, `rekap_omzet`. Seed: 20 item sayur
  (harga Medan) + 6 pelanggan (Blok A–D).
- **`agent/switch_client.py`** — client protokol Switch stdlib-only (urllib):
  registrasi agen, SSE events, heartbeat, ops.

## Web app (tampilan WA)

Buat warga yang tidak mau install aplikasi chat: buka link, langsung chat
kayak WhatsApp. `webapp/` — server stdlib port 8001 + satu file HTML:

```bash
cd webapp
python3 server.py   # http://127.0.0.1:8001 — DB demo: data/webapp.db (fresh)
```

- **Chat warga (`/`, `webapp/index.html`)** — header hijau + avatar 🥬 +
  status online, picker "Saya:" hanya berisi warga (Bu Sari, Pak Budi,
  Bu Ratna, ... — TIDAK ada opsi "Tukang Sayur"), bubble putih/hijau +
  jam, tombol cepat khusus warga (Pesan sayur, Daftar harga, Pesanan
  saya, Tagihan saya), indikator mengetik, dan link "Dashboard Tukang
  Sayur →" di atas. Total hari ini, rute, rekap omzet, dan daftar
  menunggu ACC TIDAK ada di chat ini — itu urusan tukang sayur.
- **Dashboard tukang sayur (`/vendor`, `webapp/vendor.html`)** — halaman
  terpisah khusus tukang sayur, PIN-gated: pesanan menunggu ACC (tombol
  ACC / Tolak), rekap hari ini, tagihan belum bayar (tombol Tandai Lunas
  per pesanan, pilih tunai/transfer/QRIS), rute hari ini urutan Blok A→D
  (tombol Tandai Diantar per berhenti + kartu "Berikutnya"), ubah harga &
  stok, komplain terbaru, dan status toko (Buka/Libur + jam cutoff).
  Memanggil tools SQLite asli lewat endpoint `/api/vendor/*` (semua
  PIN-gated, 403 kalau PIN salah); tidak lewat LLM. Buka di
  `http://127.0.0.1:8001/vendor`, masukkan PIN vendor — PIN demo `1234`
  kalau `BANGSAYUR_VENDOR_PIN` tidak diset; set PIN sendiri yang kuat
  dengan `BANGSAYUR_VENDOR_PIN=<PIN kamu>` sebelum dipakai sungguhan
  (PIN tidak pernah ditampilkan di halaman atau log).
- Backend-nya agen yang sama persis (`agent.run_turn` + tools SQLite) —
  jawaban, harga, dan stok identik dengan demo Switch/Mattermost.
- Terverifikasi 6/6 langkah via `/api/chat` (5 Nov 22:00): pesanan #1 Rp58.000,
  #2 Rp40.000, rekap Rp98.000, rute Blok A, tagihan Rp98.000, omzet lunas Rp0.

## Sistem aman (anti order fiktif)

Pesanan tidak pernah langsung jadi — ada 4 lapis:

1. **Pelanggan dikenal dulu** — warga baru wajib daftar (nama + blok +
   alamat) lewat `daftar_pelanggan` sebelum pesanannya dicatat.
2. **Konfirmasi** — agen mengulang ringkasan + total, pesanan baru dicatat
   setelah warga balas YA.
3. **ACC tukang sayur** — pesanan masuk status `menunggu_acc`; stok baru
   berkurang dan pesanan baru masuk rekap/rute/tagihan setelah tukang sayur
   ACC (`konfirmasi_pesanan`, aksi `acc`/`tolak`). Perintah vendor HANYA
   dari pengirim tukang sayur.

   Identitas vendor: kalau `BANGSAYUR_VENDOR_IDS` diisi (daftar ID user
   Mattermost, dipisah koma), hanya pengirim yang ID-nya ada di daftar itu
   yang dihitung sebagai tukang sayur; nama yang cocok saja TIDAK cukup.
   Kalau variabel itu kosong (mode demo), vendor dikenali dari NAMA
   pengirim saja — fallback itu hanya untuk demo dan tidak aman untuk
   produksi, karena siapa pun bisa memakai nama itu. Di web app, perintah
   vendor juga butuh `BANGSAYUR_VENDOR_PIN` (isi PIN kuat sendiri;
   kalau tidak diisi, mode demo menerima PIN demo `1234`).
4. **Catatan hitam** — `tandai_tidak_diambil`: stok dikembalikan, no_show
   pelanggan +1; 2x tidak ambil → pelanggan `ditahan`, order berikutnya
   masuk `menunggu_dp` dan baru jalan setelah tukang sayur konfirmasi
   DP masuk (`dp_masuk`).

Status pesanan: `menunggu_acc` → `dikonfirmasi` / `ditolak`;
`menunggu_dp` → `menunggu_acc`; `dikonfirmasi` → `tidak_diambil`.
Rekap/rute/tagihan/omzet HANYA menghitung `dikonfirmasi`; yang menunggu
tampil terpisah. DB lama dimigrasi otomatis (`db._migrate`): pesanan lama
dianggap `dikonfirmasi`.

Terverifikasi end-to-end via web app (5 Nov 22:30): warga baru → daftar →
YA → menunggu_acc → ACC → dikonfirmasi; tolak; 2x tidak diambil → ditahan
→ DP → ACC. Stok kembali utuh tiap tidak-diambil.

## Rute (anti bolak-balik)

`rute_hari_ini` mengurutkan berhenti: Blok A → B → C → D, di dalam blok
per jalan lalu nomor rumah (`_parse_alamat`: "Jl. Melati No. 5" sebelum
"No. 12"). Tiap berhenti membawa `status_antar` ('belum'/'diantar') plus
`berikutnya` (berhenti terdekat yang belum diantar).

- `tandai_diantar(pesanan_id)` — tukang sayur sudah sampai di rumah warga
  (hanya pesanan dikonfirmasi, hanya dari tukang sayur).
- `rute_berikutnya()` — berhenti berikutnya + sisa berhenti.
- Pesanan yang di-ACC di tengah jalan langsung masuk urutan yang benar.

Terverifikasi end-to-end via web app (5 Nov 22:45): 3 pesanan (Sari
Melati 12 duluan) dirute jadi Budi Melati 5 → Sari Melati 12 → Ratna
Kenanga 8; "berikutnya" → Budi; "sudah diantar #2" → berikutnya jadi
Sari; order susulan Dewi (Blok C) masuk paling belakang.

## Sisi lain (semua digarap 5 Nov 22:50–23:00)

- **Harga/stok harian** — `atur_harga_stok` (tukang sayur saja): "cabai
  merah naik 55 ribu, stok kangkung 20". Harga di daftar_harga sama untuk
  semua warga.
- **Singkatan warga** — alias di `_cari_item`: bamer, baput, cabe, rawit,
  telor, dll. langsung ketemu itemnya.
- **Ganti/batal** — `ubah_pesanan` / `batalkan_pesanan` untuk pesanan yang
  masih menunggu ACC (cocok nama pemilik; warga lain tidak bisa batalkan
  pesanan orang). Agen juga menggabungkan order susulan ke pesanan yang
  masih menunggu kalau warga setuju.
- **Komplain** — `catat_komplain` + `daftar_komplain` (tukang sayur).
- **Bayar** — `tandai_lunas(pesanan_id, metode)` (tunai/transfer/qris,
  tukang sayur saja); `lapor_bayar` warga → status "lapor transfer",
  TIDAK otomatis lunas sebelum verifikasi; `tandai_bon` + jatuh tempo
  (tetap masuk tagihan); `hitung_kembalian`.
- **Titip** — `tambah_catatan` ("titip ke Bu Sari") tampil di rute.
- **Libur & batas order** — `atur_status_toko` (buka/libur + pesan);
  kalau libur, pesanan baru ditolak dengan pesan tukang sayur.
  `atur_cutoff` (default 07:00): pesanan setelah jam itu otomatis
  bertanggal besok (`untuk_besok=true`).
- **Privasi** — alamat/nomor warga lain tidak pernah disebut ke warga;
  rute lengkap hanya untuk tukang sayur. Perintah vendor dienforce di
  `_execute` (bukan cuma prompt): warga yang minta ACC/lunas/ubah harga
  ditolak sistem.
- **Backup & biaya** — `buat_backup` (JSON lengkap ke data/backup-*),
  `cek_biaya` (panggilan + token per hari; harga Rupiah tidak ditampilkan
  karena tarif berubah). Token dicatat otomatis tiap balasan model.

Terverifikasi end-to-end via web app (5 Nov 22:57): update harga, ganti,
komplain, lapor bayar → lunas, bon, titip, libur → tolak pesanan, buka
lagi, backup, biaya (54 panggilan / 302.380 token).

CATATAN: server web lama sempat tetap melayani saat restart (kill by PID
kena shell sendiri) — matikan berdasarkan PORT (`fuser -k 8001/tcp`)
lalu verifikasi PID baru sebelum tes.

## Cara menjalankan (reproduce demo)

### 0. Prasyarat

- Python 3.12+, PostgreSQL 16, Node.js 20+ (untuk Switch Console, opsional)
- `BASENTEN_API_KEY` — API key Baseten untuk model Muse Spark
  (atau integrasi Secure Vault; key **tidak pernah** ditulis di repo)
- Repo Switch: `git clone https://github.com/sandbox-quantum/switch` ke
  `../switch-src` di sebelah repo ini, atau set `SWITCH_SRC` ke path-nya.
  Set juga `BANGSAYUR_HOME` kalau repo ini ada di tempat lain; semua
  script menyelesaikan path relatif terhadap repo root.

### 1. Switch Core + PostgreSQL

```bash
# PostgreSQL: database + role untuk Switch (lihat switch-src/.env.example)
sudo -u postgres psql -c "CREATE DATABASE switch;" \
  -c "CREATE ROLE switch_app LOGIN PASSWORD '...';" \
  -c "CREATE ROLE postgres LOGIN PASSWORD '...';"  # owner, sesuaikan .env

# .env Switch dari contoh + generate secrets:
#   cp switch-src/.env.example switch-src/.env
#   bash switch-src/deploy/local/generate-env-secrets.sh.env local
#   lalu isi DB_PASSWORD / DB_OWNER_PASSWORD

# Jalankan core (script ini me-load .env — `uv run` saja TIDAK me-loadnya):
bash demo/start_switch.sh
curl -s http://127.0.0.1:8000/health   # {"status":"ok"}
```

### 2. Mattermost + bridge

```bash
# Mattermost Team Edition (binary) + database `mattermost`, jalan di :8065.
# Lalu daftarkan bridge + buat team/user demo:
bash demo/setup_bridge.sh
# Script ini memakai deploy/shared_resources/setup.py dari repo Switch:
# membuat team `komplek-melati`, user `pemilik`/`warga`, dan meregistrasi
# bridge Mattermost sebagai default. Nyalakan dulu bot creation di
# Mattermost (ServiceSettings.EnableBotAccountCreation=true) — kalau tidak,
# bot agen gagal dibuat ("Bot creation has been disabled").
```

### 3. Daftarkan agen BangSayur

```bash
cd agent
python3 -c "
from switch_client import SwitchClient
import os
print(SwitchClient.register('http://127.0.0.1:8000', 'bangsayur',
      'Agen tukang sayur keliling untuk warga komplek',
      os.environ['AGENT_REGISTRATION_TOKEN']))"
# Simpan {id, api_key} ke .switch-agent.json di repo root
# (chmod 600, GITIGNORED; override dengan SWITCH_CREDS_FILE).
# Lalu buka addressing policy agen untuk semua warga:
python3 ../demo/open_addressing.py   # PUT {"policy": null} sebagai admin
# (lihat demo/open_addressing.py — agen tidak bisa mengubah setting sendiri)
```

### 4. Jalankan runner + skenario demo

```bash
cd agent
python3 run.py            # pakai .switch-agent.json + .room.json (buat room baru
                          # kalau belum ada); dengarkan room, balas mention @bangsayur
# Di terminal lain, kirim skenario sebagai warga simulasi:
python3 ../demo/run_scenario.py
# Transkrip + verifikasi DB: demo/transcript-demo.md
```

Dua room butuh dua runner (DB dan kredensial agen sama):

```bash
BANGSAYUR_ROLE=warga  python3 run.py   # room #pesan-sayur (.room.json)
BANGSAYUR_ROLE=vendor python3 run.py   # room #dapur-bangsayur (.vendor-room.json)
# Override room vendor dengan SWITCH_VENDOR_ROOM_ID=... /
# BANGSAYUR_VENDOR_ROOM_ID=... (file: SWITCH_VENDOR_ROOM_FILE).
```

Reset demo kapan saja (dari repo root): `rm data/bangsayur.db .room.json .vendor-room.json`,
lalu ulang langkah 4 (runner membuat room + channel Mattermost baru).
`.room.json`, `.vendor-room.json` dan `.switch-agent.json` sama-sama ada
di repo root (override dengan `SWITCH_ROOM_FILE` / `SWITCH_VENDOR_ROOM_FILE` /
`SWITCH_CREDS_FILE`).

## Catatan implementasi (jebakan yang sudah dilewati)

- **Ops butuh koneksi terbuka:** SSE stream harus dibuka DULU sebelum `op()`
  apa pun, kalau tidak server balas 409 "connection is not open".
- **`post_message` tanpa `room_id`:** pesan masuk ke room yang di-claim koneksi
  via `connect_to_room`.
- **Addressing default `owner_only`:** warga non-owner yang mention agen akan
  ditolak server ("I only take instructions from my owner..."). Buka lewat
  `PUT /gateway/agents/{id}/addressing-policy` dengan `{"policy": null}`
  (agen tidak bisa mengubah setting sendiri — harus admin/owner).
- **Bot Mattermost dibuat saat startup core:** agen yang didaftarkan SETELAH
  core jalan tidak langsung punya bot — restart core agar identitas
  ter-provision ("Provisioned mattermost identities for N agents"), dan
  pastikan bot creation diaktifkan di config Mattermost.
- **Bot harus member channel:** room yang dibuat sebelum bot ada tidak berisi
  bot — tambah manual via API Mattermost, atau buat room baru setelah bot ada.
- **Akun admin bridge (`pemilik`) tidak bisa bicara ke agen:** adapter Switch
  sengaja mengabaikan postingan dari admin user-nya sendiri. Untuk demo, yang
  bertanya omzet adalah akun `warga` (tukang sayurnya).
- **Proxy egress:** panggilan Baseten HARUS lewat proxy HTTP(S) VM — jangan
  unset proxy env di runner (token surrogate `hsurr:*` hanya diganti Sentinel
  di jalur proxy; tanpa proxy Baseten balas 401). Sebaliknya, `httpx` rusak
  oleh entri IPv6 bracket di `NO_PROXY` — unset proxy hanya di script yang
  memakai httpx (setup/probe), bukan di runner.
- **Nama pelanggan vs username:** username chat `busari` = pelanggan
  `Bu Sari` — `cari_pelanggan` menormalisasi spasi di kedua sisi.
- **`just run` me-load `.env`, `uv run` tidak** — dan `just` tidak ada di
  semua VM; `demo/start_switch.sh` me-load `.env` manual.

## Struktur repo

```
bangsayur/
├── README.md
├── SUBMISSION.md       # teks siap salin-tempel form submit hackathon (Inggris + arti Indonesia)
├── docker-compose.yml      # Switch + Mattermost + Postgres (butuh Docker; BELUM TERUJI — lihat header file, langkah bare-metal di atas yang terverifikasi)
├── .env.example            # contoh env, TANPA secret
├── .gitignore              # .switch-agent.json, .env, *.db, venv/, __pycache__/
├── agent/
│   ├── agent.py            # otak: tool loop Muse Spark (Baseten)
│   ├── tools.py            # 7 tools SQLite (harga/pesanan/rute/tagihan/omzet)
│   ├── db.py               # skema + seed (20 item, 6 pelanggan, Blok A-D)
│   ├── switch_client.py    # client protokol Switch (stdlib-only)
│   └── run.py              # runner: SSE + heartbeat + balas mention
├── webapp/
│   ├── server.py           # server chat WA (port 8001)
│   ├── index.html          # UI chat (warga saja)
│   └── vendor.html         # dashboard tukang sayur (PIN-gated, /vendor)
├── tests/
│   ├── test_tools.py       # unittest (stdlib saja): pesanan, privasi, uang, race
│   └── test_vendor_dashboard.py  # unittest: PIN gate vendor, endpoint vendor, pemisahan tampilan
├── docker/
│   └── postgres-init/01-mattermost.sh   # buat mmuser + DB mattermost
└── demo/
    ├── start_switch.sh     # jalankan switch-core (load .env)
    ├── setup_bridge.sh     # Mattermost + registrasi bridge Switch
    ├── run_scenario.py     # kirim 6 langkah demo sebagai warga
    ├── probe_room.py       # probe sekali-pakai (stream/room/event)
    ├── transcript-demo.md  # transkrip demo (YA→ACC, terverifikasi via simulasi lokal)
    ├── transcript-demo-EN.md  # versi Inggris, balasan agen tetap Indonesia asli + terjemahan
    ├── transcript-webapp.md  # output run_webapp_demo.py --mock
    ├── transcript-webapp-EN.md  # versi Inggris transkrip webapp (22 cek)
    ├── run_webapp_demo.py  # jalankan ulang demo 6 langkah, --mock atau --live
    ├── VIDEO_SCRIPT.md     # naskah shot-by-shot video demo <3 menit
    ├── VIDEO_SCRIPT-EN.md  # versi bilingual Inggris/Indonesia naskah video
    ├── VIDEO_NOTE.md       # cara video demo dibuat (catatan jujur)
    └── bangsayur-demo-video-v2.mp4  # video demo v2 (2 menit 5 detik)
```

## Video demo (v2 sudah direkam)

**Status: SUDAH DIREKAM — v2.** Tonton di sini:
[`demo/bangsayur-demo-video-v2.mp4`](demo/bangsayur-demo-video-v2.mp4)
(2 menit 5 detik, portrait, narasi Inggris + subtitle), atau
https://github.com/depapranata26/bangsayur/raw/main/demo/bangsayur-demo-video-v2.mp4
Teks siap salin-tempel untuk form submit ada di
[`SUBMISSION.md`](SUBMISSION.md). Video ini menampilkan desain
pemisahan yang berlaku sekarang: Bu Sari pesan di chat warga →
ringkasan + YA → menunggu ACC; vendor ACC di dashboard ber-PIN → stok
berkurang; Pak Budi dengan alur yang sama; omzet vendor Rp98.000 dan
rute Pak Budi Jl. Melati No. 5 dulu, baru Bu Sari No. 12; Bu Ratna
tanya rekap (hanya miliknya, 0).

Video ini adalah **demo web app**, BUKAN rekaman live Mattermost —
balasan agen disusun dari hasil tool SQLite asli (21/21 cek). Lihat
[`demo/VIDEO_NOTE.md`](demo/VIDEO_NOTE.md) untuk cara videonya dibuat.
Jangan klaim ini rekaman live Mattermost sampai ada rekaman live
beneran. Transkrip pendampingnya ada di
`demo/transcript-demo.md` — itu **bukan log live Mattermost**, melainkan
transkrip yang terverifikasi via simulasi lokal
(`python3 demo/run_webapp_demo.py --mock`, 22 cek). Jalankan ulang
dengan:

```bash
python3 demo/run_webapp_demo.py --mock   # tanpa model, tanpa Switch/Mattermost
python3 demo/run_webapp_demo.py --live [--vendor-pin <PIN>]  # butuh Baseten
```

## Kenapa Switch yang utama (dan web app hanya pintu alternatif)

- **Switch + Mattermost adalah jalur utama**, karena di situlah grup chat
  warga tinggal: room warga (`#pesan-sayur`) ditambah room khusus vendor
  (`#dapur-bangsayur`), agen membalas sebutan `@bangsayur`, dan identitas
  pengirim berasal dari akun Mattermost masing-masing. Semua alur (pesan
  → YA → ACC → rute → tagihan) dirancang untuk room-room itu — warga
  tidak pernah melihat rekap, rute, atau tagihan tukang sayur, dan
  tukang sayur tidak bekerja di dalam chat warga.
- **Web app (`webapp/server.py`) hanya pintu alternatif / alat demo.**
  Agennya SAMA (`agent.run_turn` yang sama, tools SQLite yang sama),
  tapi: (1) satu pengguna dalam satu waktu — pengirim dipilih lewat
  picker "Saya", bukan dari akun chat beneran; (2) DB-nya terpisah
  (`data/webapp.db`, bukan `data/bangsayur.db`); (3) tidak ada room/grup,
  jadi dinamika multi-warga hanya simulasi. Web app berguna untuk demo
  dari HP dan tes cepat tanpa menjalankan Switch/Mattermost — bukan
  pengganti jalur utama.

## Tes

```bash
python3 -m py_compile agent/*.py webapp/server.py demo/*.py tests/*.py
python3 -m unittest discover -s tests -v
```

`tests/test_tools.py` (unittest, stdlib saja, DB temp di /tmp) mencakup:
pesanan → ACC mengurangi stok tepat sekali, ACC kedua ditolak, privasi
scoped (warga hanya lihat rekap/tagihan/pesanannya sendiri, alamat
diredaksi), pesanan orang lain tidak bisa diubah, catatan di-append,
kembalian desimal tepat, varian parsing alamat, race stok dua thread yang
tidak boleh oversell, `run_turn` yang kehabisan iterasi membalas dengan
kalimat maaf bukan JSON mentah, WIB (`Asia/Jakarta`), dan cek vendor-ID.
`tests/test_vendor_dashboard.py` mencakup pemisahan: endpoint vendor
tanpa PIN atau PIN salah balas 403 tanpa bocor data, ACC lewat endpoint
mengurangi stok tepat sekali, Tandai Diantar hanya untuk pesanan
dikonfirmasi, ubah harga butuh PIN vendor, dan chat warga tidak berisi
chip vendor atau opsi picker tukang sayur sementara `/vendor` PIN-gated
dan HTML-nya tidak berisi nilai PIN.

## Keterbatasan yang diketahui

- **Video demo v2 adalah demo web app, bukan live** (lihat atas dan
  `demo/VIDEO_NOTE.md`); transkrip terverifikasi via simulasi lokal,
  bukan log live. Catatan: naskah video
  (`demo/VIDEO_SCRIPT.md`, `demo/VIDEO_SCRIPT-EN.md`) ditulis SEBELUM
  pemisahan warga/vendor — naskah itu menampilkan alur satu chat lama.
  Pemisahan (chat warga + dashboard vendor, dua room Switch) adalah
  desain yang berlaku sekarang, dan video v2 sudah mengikutinya;
  naskah lama hanya disimpan sebagai acuan untuk rekaman ulang live
  dari HP di masa depan.
- **Dua room Switch belum dites live.** Desain, dukungan runner
  `BANGSAYUR_ROLE`, dan helper `resolve_vendor_room_id` sudah ada dan
  terdokumentasi, tapi belum ada run live Mattermost/Switch yang
  membuktikan alur dua room end-to-end.
- **Mode live skrip demo (`--live`) belum dijalankan** di sesi ini
  (tidak ada panggilan model Baseten); yang terverifikasi hanya `--mock`
  (22 cek lolos). Jalankan `--live` sekali sebelum mengklaim alur web
  app end-to-end dengan model.
- **Auth vendor:** kalau `BANGSAYUR_VENDOR_IDS` diisi, vendor dikenali
  dari ID pengguna; kalau kosong (mode demo), dari NAMA pengirim saja —
  nama bisa dipalsu siapa pun, jadi mode demo JANGAN dipakai di
  produksi. Di web app, perintah vendor juga digerbangi
  `BANGSAYUR_VENDOR_PIN` (kosong = mode demo, PIN demo `1234` diterima).
  Isi PIN kuat sendiri sebelum dipakai beneran; jangan commit `.env`
  yang sudah terisi.
- **Batas order:** pesanan setelah 07:00 WIB otomatis jadi pesanan BESOK
  (`untuk_besok=true`). Skrip demo membaca tanggal pesanan dari DB
  supaya rekap/rute tetap cocok walau dijalankan setelah cutoff.
- **`docker-compose.yml` TETAP BELUM TERUJI.** File-nya valid YAML
  (`python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"`
  → OK), tapi tidak ada Docker di VM pengembangan, jadi belum pernah
  dijalankan end-to-end. Jangan jadikan compose jalur reproduksi utama;
  jalur terverifikasi tetap langkah bare-metal di atas.
- **Race stok dan reconnect SSE sudah diperbaiki di kode dan dicover tes
  lokal** (transaksi `BEGIN IMMEDIATE`; reconnect dengan backoff
  2/5/10/30 detik, maks 5 kali; retry model hanya untuk 429/500/502/503),
  tapi keduanya belum dibuktikan terhadap Switch/Mattermost live.

## Yang TIDAK di-commit

`.env`, `.switch-agent.json` (api_key agen), `.room.json`,
`.vendor-room.json`, `*.db`,
`demo/venv/`, `__pycache__/`. Demo password Mattermost (`warga-pw`,
`pemilik-pw`) hanya untuk lingkungan demo lokal — ganti di deployment nyata.
