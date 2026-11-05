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
transkrip penuh di [`demo/transcript-demo.md`](demo/transcript-demo.md):

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
Warga (Mattermost) ──bridge──> Switch Core (room) ──SSE──> agent/run.py
                                                              │
                                              Muse Spark (Baseten)
                                                              │ tool calls
                                                        SQLite (data/*.db)
```

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

- Header hijau + avatar 🥬 + status online, picker "Saya:" (Bu Sari, Pak Budi,
  Bu Ratna, ...), bubble putih/hijau + jam, tombol cepat (Pesan sayur, Daftar
  harga, Total hari ini, Rute, Belum bayar, Rekap omzet), indikator mengetik.
- Backend-nya agen yang sama persis (`agent.run_turn` + tools SQLite) —
  jawaban, harga, dan stok identik dengan demo Switch/Mattermost.
- Terverifikasi 6/6 langkah via `/api/chat` (5 Nov 22:00): pesanan #1 Rp58.000,
  #2 Rp40.000, rekap Rp98.000, rute Blok A, tagihan Rp98.000, omzet lunas Rp0.

## Cara menjalankan (reproduce demo)

### 0. Prasyarat

- Python 3.12+, PostgreSQL 16, Node.js 20+ (untuk Switch Console, opsional)
- `BASENTEN_API_KEY` — API key Baseten untuk model Muse Spark
  (atau integrasi Secure Vault; key **tidak pernah** ditulis di repo)
- Repo Switch: `git clone https://github.com/sandbox-quantum/switch` ke
  `~/workspace/switch-src` (atau sesuaikan path di script demo)

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
# Simpan {id, api_key} ke .switch-agent.json (chmod 600, GITIGNORED).
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

Reset demo kapan saja: `rm data/bangsayur.db .room.json`, lalu ulang langkah 4
(runner membuat room + channel Mattermost baru).

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
├── docker-compose.yml      # Switch + Mattermost + Postgres (butuh Docker)
├── .env.example            # contoh env, TANPA secret
├── .gitignore              # .switch-agent.json, .env, *.db, venv/, __pycache__/
├── agent/
│   ├── agent.py            # otak: tool loop Muse Spark (Baseten)
│   ├── tools.py            # 7 tools SQLite (harga/pesanan/rute/tagihan/omzet)
│   ├── db.py               # skema + seed (20 item, 6 pelanggan, Blok A-D)
│   ├── switch_client.py    # client protokol Switch (stdlib-only)
│   └── run.py              # runner: SSE + heartbeat + balas mention
└── demo/
    ├── start_switch.sh     # jalankan switch-core (load .env)
    ├── setup_bridge.sh     # Mattermost + registrasi bridge Switch
    ├── run_scenario.py     # kirim 6 langkah demo sebagai warga
    ├── probe_room.py       # probe sekali-pakai (stream/room/event)
    └── transcript-demo.md  # transkrip demo terverifikasi
```

## Yang TIDAK di-commit

`.env`, `.switch-agent.json` (api_key agen), `.room.json`, `*.db`,
`demo/venv/`, `__pycache__/`. Demo password Mattermost (`warga-pw`,
`pemilik-pw`) hanya untuk lingkungan demo lokal — ganti di deployment nyata.
