# BangSayur Demo Video Script — Bilingual (English / Indonesian)

Status: **NOT RECORDED YET.** Follow this script as written; total
length **2 minutes 58 seconds** (178 seconds).

This is the English version of [`demo/VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md).
The shots, order, on-screen actions and total duration are unchanged.
Only the narration is translated into English so the judges can follow
it.

**How to use this file:** the narration Depa reads out loud is in
**English** (short sentences, easy words). Under each English line,
*Arti:* gives the Indonesian meaning so Depa understands what he is
saying. The text typed in the chat stays in **Indonesian**, because
that is what the residents really type — the English meaning of each
chat message is given next to it.

## What is recorded

The video is recorded from the **BangSayur web app in a phone browser**
(a WhatsApp-style chat), NOT from live Mattermost — because the live
Switch/Mattermost path needs a running server and was not used for
this recording. If it is later re-recorded through live Mattermost,
replace Shot 0 with the Mattermost channel screen and say so in the
narration. Do not claim this video is a live Mattermost recording.

The flow shown is the flow the current code REQUIRES: summary + ask
for YA ("yes") → only after YA is the order recorded (menunggu_acc =
"waiting for approval") → vendor ACC → dikonfirmasi ("confirmed"),
and stock is ONLY reduced at ACC. Scoped privacy: Bu Ratna only sees
her own orders; the revenue recap and the route are vendor-only.

## Pronunciation tips (read English slowly, one line at a time)

- **BangSayur** — say "bahng sah-YOOR" (Bang = like "bung", Sayur = sah-YOOR).
- **kangkung** — "kahng-KOONG" (water spinach).
- **cabai** — "chah-BYE" (chili).
- **tempe** — "TEM-peh" (tempeh).
- **Rp58.000** — say "fifty-eight thousand rupiah". Rp98.000 is
  "ninety-eight thousand rupiah". Rp40.000 is "forty thousand rupiah".
- **YA** — say the letters "Y-A", or say "yes". Both are fine.
- **ACC** — say the letters "A-C-C", or say "approve". Both are fine.
- If a word feels hard, say it slowly. A slow, clear voice is better
  than a fast, unclear one.

## Preparation (before pressing record)

1. Run the web app with a clean demo database (not the production
   `data/webapp.db`), for example:
   `python3 demo/run_webapp_demo.py --live` (server + temp DB in /tmp),
   or `BANGSAYUR_WEB_PORT=8001 python3 webapp/server.py` then open
   `http://<server-address>:8001` in the phone browser.
2. Phone: Do Not Disturb on, notifications off, full screen brightness,
   hold the phone upright (portrait). Use the phone's built-in screen
   recorder.
3. Prepare the message texts below (copy-paste from your notes so you
   do not mistype during the recording). Type slowly so viewers can
   follow.
4. When you switch to the sender **Tukang Sayur** (the vendor), the app
   asks for the vendor PIN (demo: `1234`) — type it when asked; the PIN
   does not show on screen.
5. Cut the model loading pauses ("BangSayur mengetik..." / "BangSayur
   is typing...") when editing, but NEVER cut the content of the
   agent's replies.

## Shot-by-shot

### Shot 0 — Opening (0:00–0:10, 10 seconds)

- **Screen:** BangSayur web app (header "BangSayur • online", welcome
  bubble "Halo! Saya Bang Sayur..." / "Hello! I am Bang Sayur..."),
  sender picker at the top right still on "Bu Sari".
- **Narration (English, read out loud):**
  "This is BangSayur — a vegetable seller agent in a group chat.
  Order vegetables, vendor approval, and the delivery route, all in
  the chat. This is the demo."
- **Arti:** "Ini BangSayur — agen tukang sayur keliling di grup chat
  warga. Pesan sayur, ACC tukang sayur, sampai rute antar, semua lewat
  chat. Ini demonya."
- **Action:** stay still for 2 seconds, then scroll a little up and
  down so viewers can see this is a real chat app.

### Shot 1 — Bu Sari orders, the agent asks for YA confirmation (0:10–0:35, 25 seconds)

- **Screen:** sender picker = **Bu Sari**. Type and send:
  "halo bang, saya mau pesan 2 ikat kangkung sama 1 kg cabai merah"
  *(EN: "Hi, I want to order 2 bunches of kangkung and 1 kg of red chili.")*
  The agent replies: summary of 2 bunches of kangkung Rp10.000 +
  1 kg red chili Rp48.000, total Rp58.000, ending with
  "Betul? Balas YA." *(EN: "Is that right? Reply YA [yes].")*
- **Narration (English):**
  "Bu Sari orders two bunches of kangkung and one kilo of red chili.
  The agent does not record it at once. First it repeats the summary
  and asks for confirmation."
- **Arti:** "Bu Sari pesan 2 ikat kangkung dan 1 kilo cabai merah.
  Agen tidak langsung mencatat — dia ulang dulu ringkasannya dan minta
  konfirmasi."
- **Action:** hold the screen for 3 seconds on the summary reply so
  the total Rp58.000 is easy to read.

### Shot 2 — Bu Sari replies YA, the order waits for ACC (0:35–1:00, 25 seconds)

- **Screen:** send "YA" *(EN: "YES.")* Reply: "Pesanan #1 sudah
  dicatat ya Bu Sari ... Status: menunggu ACC Bang Sayur"
  *(EN: "Order #1 is recorded, Bu Sari ... Status: waiting for
  Bang Sayur's approval.")*
- **Narration (English):**
  "After Bu Sari says yes, the order is in — but its status is still
  waiting for approval. Note this: the stock has not dropped yet, so
  an order that is cancelled costs no stock."
- **Arti:** "Setelah Bu Sari balas YA, pesanan masuk — tapi statusnya
  masih menunggu ACC. Perhatikan: stok belum berkurang di tahap ini,
  jadi pesanan yang tidak jadi tidak menggerogoti stok."
- **Action:** tap gently on the "menunggu ACC" line if needed.

### Shot 3 — The vendor approves (ACC), stock drops only now (1:00–1:25, 25 seconds)

- **Screen:** change the sender picker to **Tukang Sayur** (enter the
  demo vendor PIN `1234` when asked). Send "ACC #1"
  *(EN: "Approve #1.")* Reply: "Pesanan #1 Bu Sari sudah di-ACC dan
  dikonfirmasi" *(EN: "Order #1 for Bu Sari is approved and
  confirmed.")*
- **Narration (English):**
  "Now the vendor approves it. Only at this point is the order
  confirmed — and the kangkung stock drops from 30 to 28, the red
  chili from 8 to 7."
- **Arti:** "Sekarang tukang sayurnya yang ACC. Baru di titik inilah
  pesanan dikonfirmasi — dan stok kangkung berkurang dari 30 jadi 28,
  cabai merah dari 8 jadi 7."
- **Action:** if there is time, open the price list briefly (chip
  "Daftar harga" / "Price list") to show the stock after ACC; if time
  is tight, skip it — the narration already says it.

### Shot 4 — Pak Budi: order, YA, ACC (1:25–1:50, 25 seconds)

- **Screen:** picker to **Pak Budi**. Send "bang, saya mau 1 kg telur
  ayam sama 2 papan tempe"
  *(EN: "I want 1 kg of chicken eggs and 2 blocks of tempeh.")*
  → summary Rp40.000 → send "YA" *(EN: "YES.")* → order #2 waits for
  ACC → picker to **Tukang Sayur**, send "ACC #2"
  *(EN: "Approve #2.")* → confirmed.
- **Narration (English):**
  "Pak Budi orders one kilo of eggs and two blocks of tempeh, forty
  thousand rupiah. The flow is the same: summary, yes, then the
  vendor approves."
- **Arti:** "Pak Budi pesan sekilo telur dan dua papan tempe,
  empat puluh ribu. Alurnya sama: ringkasan, YA, lalu ACC tukang
  sayur."
- **Action:** speed it up by cutting the typing pauses (jump cuts);
  the important part is that all four reply bubbles are visible.

### Shot 5 — Bu Ratna asks for her recap: only her own (1:50–2:10, 20 seconds)

- **Screen:** picker to **Bu Ratna**. Send "bang, rekap hari ini
  berapa? sama tagihan saya?"
  *(EN: "What is today's recap? And what is my bill?")*
  Reply: 0 orders, revenue Rp0, no bill yet. There is NO mention of
  Bu Sari / Pak Budi in that reply.
- **Narration (English):**
  "Bu Ratna has not ordered today. What she sees is only her own —
  zero. Her neighbours' orders do not leak to her."
- **Arti:** "Bu Ratna belum pesan hari ini. Yang dia lihat cuma
  miliknya sendiri — nol. Pesanan tetangga tidak bocor ke dia."
- **Action:** hold the screen for 3 seconds on Bu Ratna's recap reply.

### Shot 6 — The vendor asks for the revenue recap: sees everything (2:10–2:30, 20 seconds)

- **Screen:** picker to **Tukang Sayur**. Send "rekap omzet hari ini
  dong" *(EN: "Give me today's revenue recap.")* Reply: 2 orders,
  revenue Rp98.000, paid Rp0, unpaid Rp98.000, per-item breakdown +
  the order list for Bu Sari and Pak Budi.
- **Narration (English):**
  "Now the vendor asks: today's revenue is ninety-eight thousand
  rupiah, two orders, all unpaid."
- **Arti:** "Giliran tukang sayur yang tanya: omzet hari ini sembilan
  puluh delapan ribu, dua pesanan, semuanya belum bayar."
- **Action:** scroll slowly so the order list is easy to read.

### Shot 7 — The vendor asks for the route (2:30–2:50, 20 seconds)

- **Screen:** still as **Tukang Sayur**. Send "rute hari ini gimana?"
  *(EN: "What is today's route?")* Reply: Block A, 2 stops —
  Pak Budi, Jl. Melati No. 5 first, then Bu Sari, Jl. Melati No. 12;
  "Berikutnya: Pak Budi" *(EN: "Next: Pak Budi.")*
- **Narration (English):**
  "The route is already sorted, so the vendor does not go back and
  forth: the smaller house number comes first. The full route with
  addresses is only for the vendor — ordinary residents cannot ask
  for it."
- **Arti:** "Rutenya sudah urut supaya tidak bolak-balik: nomor rumah
  kecil dulu. Rute lengkap dengan alamat ini hanya untuk tukang sayur —
  warga biasa tidak bisa memintanya."
- **Action:** hold the screen for 3 seconds on the route reply.

### Shot 8 — Closing (2:50–2:58, 8 seconds)

- **Screen:** back to the chat view (picker on Bu Sari).
- **Narration (English):**
  "BangSayur: order in the chat, vendor approval, stock and revenue
  recorded neatly. Thank you!"
- **Arti:** "BangSayur: pesan lewat chat, ACC tukang sayur, stok dan
  omzet tercatat rapi. Terima kasih!"
- **Action:** stop recording.

## Total duration

| Shot | Content | Duration |
|------|---------|----------|
| 0 | Opening | 10 sec |
| 1 | Bu Sari orders + summary | 25 sec |
| 2 | YA → waiting for ACC | 25 sec |
| 3 | Vendor ACC → stock drops | 25 sec |
| 4 | Pak Budi orders + YA + ACC | 25 sec |
| 5 | Bu Ratna: only her own recap | 20 sec |
| 6 | Vendor: revenue recap Rp98.000 | 20 sec |
| 7 | Vendor: route | 20 sec |
| 8 | Closing | 8 sec |
| **Total** | | **178 sec = 2 min 58 sec** |

## Check before upload

- [ ] Total Rp58.000 + Rp40.000 = Rp98.000 is readable in Shots 1, 4, and 6.
- [ ] The words "menunggu ACC" ("waiting for approval") are visible in Shot 2, before Shot 3.
- [ ] Bu Ratna's reply (Shot 5) does NOT show anyone else's name or order.
- [ ] The route (Shot 7) is in order: Pak Budi No. 5 first, then Bu Sari No. 12.
- [ ] No API key, password, or PIN is visible on screen (the vendor PIN is typed through a prompt and does not show).
- [ ] The video title/description says "demo via web app (local simulation)", not "live Mattermost recording", until a real live recording exists.

Indonesian original: [`demo/VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md).
