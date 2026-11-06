# BangSayur — Hackathon Submission Text

> How to use this file: copy the **English** text under each heading
> into the hackathon submission form. The **Arti** (Indonesian meaning)
> under each section is only for Depa, so he understands what he is
> submitting — do NOT paste the Arti lines into the form.
>
> Repo: https://github.com/depapranata26/bangsayur

---

## Project name

BangSayur

*Arti: Nama proyek: BangSayur.*

## Track

Track 01 — Best Business Workflow

*Arti: Track 01 — Alur Kerja Bisnis Terbaik.*

## One-line description

A vegetable-vendor agent that lives in a residents' group chat: it
takes orders, asks for confirmation, waits for the vendor's approval,
then plans the delivery route and tracks bills and revenue.

*Arti: Agen tukang sayur yang tinggal di grup chat warga: menerima
pesanan, meminta konfirmasi, menunggu ACC tukang sayur, lalu menyusun
rute antar dan mencatat tagihan serta omzet.*

## What it does

Residents of a housing complex order vegetables in a group chat, and
BangSayur — an AI agent in that group — records the orders, sums up
the daily total, plans delivery routes per block, chases unpaid bills,
and recaps revenue. Every answer comes from a SQLite database through
tool calls, so prices, totals, and stock are never made up.

An order is never final at once. The agent repeats the summary and
total, and only records the order after the resident replies YA
("yes"). The order then waits for the vendor's approval (ACC); stock
is only reduced, and the order only enters recaps, routes, and bills,
after the vendor approves. If a customer does not pick up an order
twice, they are held and their next order needs a down payment (DP)
first. Residents only see their own orders, recaps, and bills; the
full route with addresses is vendor-only.

The demo flow: Bu Sari orders 2 bunches of kangkung (Rp10.000) and
1 kg of red chili (Rp48.000) — total Rp58.000 — replies YA, the vendor
approves, and stock drops (kangkung 30 -> 28, red chili 8 -> 7).
Pak Budi orders 1 kg of chicken eggs (Rp28.000) and 2 blocks of
tempeh (Rp12.000) — total Rp40.000 — the same way. Confirmed revenue
is Rp98.000, paid Rp0, unpaid Rp98.000. The route is Block A, 2 stops,
in address order: Pak Budi, Jl. Melati No. 5 first, then Bu Sari,
Jl. Melati No. 12.

*Arti: Warga komplek pesan sayur di grup chat, dan BangSayur — agen AI
di grup itu — mencatat pesanan, menjumlahkan total harian, menyusun
rute antar per blok, menagih yang belum bayar, dan merekap omzet.
Semua jawaban berasal dari database SQLite lewat tool call, jadi harga,
total, dan stok tidak pernah dikarang.*
*Pesanan tidak pernah langsung final. Agen mengulang ringkasan dan
total, dan baru mencatat pesanan setelah warga balas YA. Pesanan lalu
menunggu ACC tukang sayur; stok baru berkurang, dan pesanan baru masuk
rekap, rute, dan tagihan, setelah tukang sayur ACC. Kalau pelanggan
2 kali tidak mengambil pesanan, dia ditahan dan pesanan berikutnya
wajib DP dulu. Warga hanya melihat pesanan, rekap, dan tagihannya
sendiri; rute lengkap dengan alamat hanya untuk tukang sayur.*
*Alur demo: Bu Sari pesan 2 ikat kangkung (Rp10.000) dan 1 kg cabai
merah (Rp48.000) — total Rp58.000 — balas YA, tukang sayur ACC, stok
berkurang (kangkung 30 -> 28, cabai merah 8 -> 7). Pak Budi pesan 1 kg
telur ayam (Rp28.000) dan 2 papan tempe (Rp12.000) — total Rp40.000 —
dengan alur yang sama. Omzet yang dikonfirmasi Rp98.000, lunas Rp0,
belum bayar Rp98.000. Rutenya Blok A, 2 berhenti, urut alamat: Pak
Budi, Jl. Melati No. 5 dulu, baru Bu Sari, Jl. Melati No. 12.*

## How Switch is used

Switch is central to this project: without it, there is no group
room and no agent in the residents' chat.

- Switch Core runs the room **Warung Sayur - Komplek Melati**, bridged
  to Switch's built-in Mattermost channel, so residents and the vendor
  talk in one group conversation.
- BangSayur joins that room as a custom agent through the Switch agent
  protocol (`agent/switch_client.py`, stdlib-only): it registers with
  `POST /agents`, opens the SSE event stream, sends a heartbeat,
  claims the room with `connect_to_room`, listens for messages that
  mention `@bangsayur`, runs the tool loop, and replies with
  `post_message`.
- The agent's addressing policy is opened by an admin
  (`PUT /gateway/agents/{id}/addressing-policy` with `{"policy": null}`),
  so every resident in the room can mention the agent — by default
  Switch only lets the owner address it.
- The agent's brain is Muse Spark (`meta-models/muse-spark-open-1026`)
  via Baseten, driving 29 SQLite tools (`agent/tools.py`): prices,
  orders, daily recap, route, unpaid bills, mark paid, revenue, price
  and stock updates, edit/cancel, complaints, payments, delivery
  notes, closed days, order cutoff, backup, and cost tracking.
- Vendor commands (approve, mark paid, change prices) are enforced in
  code (`agent._execute`), not only in the prompt. With
  `BANGSAYUR_VENDOR_IDS` set, the vendor is recognised by user ID;
  in the web app, vendor commands also need the vendor PIN.
- A WhatsApp-style web app (`webapp/`) runs the same agent backend for
  a phone demo, but it is only an alternative door: one user at a
  time, a separate database, and no real group room. The Switch +
  Mattermost room is the main path.

*Arti: Switch adalah pusat proyek ini: tanpa Switch, tidak ada room
grup dan tidak ada agen di chat warga.*
*- Switch Core menjalankan room **Warung Sayur - Komplek Melati**,
dijembatani ke channel Mattermost bawaan Switch, supaya warga dan
tukang sayur ngobrol dalam satu grup.*
*- BangSayur masuk ke room itu sebagai agen custom lewat protokol agen
Switch (`agent/switch_client.py`, stdlib saja): daftar lewat
`POST /agents`, buka SSE event stream, kirim heartbeat, klaim room
dengan `connect_to_room`, dengarkan pesan yang menyebut `@bangsayur`,
jalankan tool loop, dan balas dengan `post_message`.*
*- Addressing policy agen dibuka oleh admin
(`PUT /gateway/agents/{id}/addressing-policy` dengan
`{"policy": null}`), supaya semua warga di room bisa menyebut agen —
secara default Switch hanya mengizinkan owner yang menyapa agen.*
*- Otak agen adalah Muse Spark (`meta-models/muse-spark-open-1026`)
lewat Baseten, menggerakkan 29 tool SQLite (`agent/tools.py`): harga,
pesanan, rekap harian, rute, tagihan belum bayar, tandai lunas, omzet,
ubah harga dan stok, edit/batal, komplain, pembayaran, catatan antar,
hari libur, batas order, backup, dan pantau biaya.*
*- Perintah vendor (ACC, tandai lunas, ubah harga) ditegakkan di kode
(`agent._execute`), bukan cuma di prompt. Kalau
`BANGSAYUR_VENDOR_IDS` diset, vendor dikenali dari user ID; di web
app, perintah vendor juga butuh PIN vendor.*
*- Web app gaya WhatsApp (`webapp/`) menjalankan backend agen yang
sama untuk demo dari HP, tapi itu hanya pintu alternatif: satu
pengguna sekali waktu, database terpisah, dan tidak ada room grup
beneran. Room Switch + Mattermost adalah jalur utama.*

## How to run

Full steps are in [`README.md`](README.md) ("How to run"). In short:
Python 3.12+ (`pip install -r requirements.txt`), PostgreSQL 16, a
`BASENTEN_API_KEY`, and the Switch repo next to this repo (see
`../switch-src` / `SWITCH_SRC`). Then: `bash demo/start_switch.sh`,
`bash demo/setup_bridge.sh`, register the agent, and `python3 agent/run.py`.
Re-run the demo checks without a model or Switch with:

```
python3 -m unittest discover -s tests -v   # 12 tests
python3 demo/run_webapp_demo.py --mock     # 22 checks
```

*Arti: Langkah lengkap ada di [`README.md`](README.md) ("How to
run"). Singkatnya: Python 3.12+ (`pip install -r requirements.txt`),
PostgreSQL 16, `BASENTEN_API_KEY`, dan repo Switch di sebelah repo ini
(lihat `../switch-src` / `SWITCH_SRC`). Lalu: `bash
demo/start_switch.sh`, `bash demo/setup_bridge.sh`, daftarkan agen, dan
`python3 agent/run.py`. Jalankan ulang cek demo tanpa model atau Switch
dengan perintah di atas (12 tes, 22 cek).*

## Demo video

https://github.com/depapranata26/bangsayur/raw/main/demo/bangsayur-demo-video-v2.mp4

Demo video v2 (2 min 5 sec, portrait, English narration + subtitles,
also in the repo at `demo/bangsayur-demo-video-v2.mp4`). It shows the
current split design: residents order in the chat (Bu Sari Rp58,000,
YA, waiting for ACC), the vendor works in the PIN-gated dashboard
(approves order #1, stock drops only at ACC, revenue Rp98,000, route
Pak Budi Jl. Melati No. 5 first, then Bu Sari No. 12), and Bu Ratna
only sees her own data. Honest note: this is a web-app demo with agent
replies scripted from real SQLite tool results (21/21 checks) — not a
live LLM / live Mattermost recording. See `demo/VIDEO_NOTE.md` for how
it was made. For the submission form, upload this file to YouTube /
Drive / Loom if the form needs a streaming link, and use that link
instead of the raw GitHub file link.

The demo transcript (English, with the agent's original Indonesian
replies and translations) is in
[`demo/transcript-demo-EN.md`](demo/transcript-demo-EN.md); the
Indonesian original is in
[`demo/transcript-demo.md`](demo/transcript-demo.md). The transcript
was verified via local simulation
(`python3 demo/run_webapp_demo.py --mock`, 22 checks) — it is not a
live Mattermost log.

*Arti: Video demo v2 (2 menit 5 detik, portrait, narasi Inggris +
subtitle) ada di repo, `demo/bangsayur-demo-video-v2.mp4`, atau di link
di atas. Video ini menampilkan desain pemisahan yang berlaku sekarang
(chat warga + dashboard vendor). Jujur: ini demo web app dengan
balasan agen yang disusun dari hasil tool SQLite asli (21/21 cek) —
bukan rekaman live LLM / live Mattermost. Lihat `demo/VIDEO_NOTE.md`.*
*Transkrip demo (bahasa Inggris, dengan balasan asli agen dalam bahasa
Indonesia plus terjemahan) ada di
[`demo/transcript-demo-EN.md`](demo/transcript-demo-EN.md); versi
Indonesia aslinya di [`demo/transcript-demo.md`](demo/transcript-demo.md).
Transkrip itu terverifikasi via simulasi lokal
(`python3 demo/run_webapp_demo.py --mock`, 22 cek) — bukan log live
Mattermost.*

## Repository

https://github.com/depapranata26/bangsayur

*Arti: Repo: https://github.com/depapranata26/bangsayur*

## Known limitations (stated honestly)

- The demo video (v2) is a web-app demo, not a live LLM / live
  Mattermost recording; see `demo/VIDEO_NOTE.md` for how it was made.
- The transcript is verified via local simulation, not a live
  Mattermost log.
- `docker-compose.yml` is valid YAML but untested (no Docker in the
  development VM); the verified reproduction path is the bare-metal
  steps in the README.
- Stock-race and SSE-reconnect fixes are covered by local tests but
  have not been proven against live Switch/Mattermost yet.

*Arti: Keterbatasan yang diketahui (ditulis jujur):*
*- Video demo (v2) adalah demo web app, bukan rekaman live LLM / live
Mattermost; lihat `demo/VIDEO_NOTE.md` tentang cara videonya dibuat.*
*- Transkrip terverifikasi via simulasi lokal, bukan log live
Mattermost.*
*- `docker-compose.yml` YAML-nya valid tapi belum teruji (tidak ada
Docker di VM pengembangan); jalur reproduksi yang terverifikasi adalah
langkah bare-metal di README.*
*- Perbaikan race stok dan reconnect SSE sudah ditutup tes lokal, tapi
belum dibuktikan terhadap Switch/Mattermost live.*
