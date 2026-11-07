# VIDEO_NOTE.md — How the BangSayur demo videos were made

## v3 (current) — `~/workspace/bangsayur-demo-video-v3.mp4`
(2 min 48 s, 720×1558 portrait, h264 + AAC, 3.8 MB)

**What changed from v2:** v2's frames were PIL renders, not real
browser output. v3 is recorded LIVE IN THE BROWSER: a real Chromium
(Playwright 1.64.1, Chrome Headless Shell 156) drove the REAL
`webapp/index.html` and `webapp/vendor.html` — typing messages,
clicking send, filling the vendor PIN, clicking ACC — and every
frame is a genuine browser screenshot (390×844 @2x, 12 shots).
This fixes the exact thing the submission form asks for ("show the
agent working in a real chat"): the app is really running and
really being used, in real time, instead of pre-rendered frames.
The flow, shots, and numbers are the same as v2.

**How it was built:** `/tmp/video-demo/mock_server.py` (rebuilt
after the VM wiped /tmp) serves the real webapp pages; `/api/chat`
is answered rule-based from the real SQLite tools via
`agent._execute` (same enforcement/privacy path as `run_turn`),
and `/api/vendor/*` is used as-is from `webapp/server.py`
(PIN-gated). `drive_playwright.py` drove the browser and verified
**9/9 checks** live in the page (Rp58.000 / Rp40.000 / Rp98.000;
stock Kangkung 30→28, Cabai 8→7, Telur 15→14, Tempe 20→18, only
after ACC; route Budi No. 5 then Sari No. 12; Ratna 0/Rp0).
Narration is English TTS, one voice (`avocado_v2:MAI_03`, speed
90), 13 clips, 148.5 s total (first draft was 212.6 s and was cut
to fit under 3 minutes). Subtitles burned in (PlayRes 720×1558,
FontSize 30, 3 short cues per shot, WrapStyle 0 — the first burn
used WrapStyle 2 and the subtitles ran off the frame; fixed and
re-burned, then re-verified). `assemble_v3.py` + `fix_subs_v3.py`
built the video. Verification frames extracted at 5 s (title),
70 s (dashboard menunggu ACC), 145 s (route, rekap Rp98.000),
160 s (Ratna 0/Rp0) — all readable, numbers correct, subtitles
inside the frame. Audio confirmed present (mean −28.4 dB,
peak −5.0 dB). `python3 -m py_compile` passes for all scripts.
Working files: `/tmp/video-demo/` (`mock_server.py`,
`drive_playwright.py`, `assemble_v3.py`, `fix_subs_v3.py`,
`title_v3.py`, `narr-v3/`, `shots-v3/`, `checks-v3.json`).
Note: Playwright's own Chromium works in this VM; the Hatch
`/opt/meta-chromium/chrome` CLI still cannot start (WebGL policy),
and `browser.browse` was NOT used — a subagent cannot operate the
live browser, so the recording used Playwright directly.

**Two honest details about the recording:**
- The demo was recorded in the evening, after the app's 07:00 order
  cutoff — orders would have been dated tomorrow, so the
  "today" recap/route would have shown Rp0. The mock server sets
  the cutoff to 23:59 through the app's own `atur_cutoff` setting,
  so the demo orders stay dated today — the same numbers the app
  shows when the demo is run in the morning (as v1/v2 were).
- The agent replies are still tool-based, not live LLM (Baseten
  unavailable in this VM, credential 403), and this is still the
  web app, not live Mattermost/Switch. The title card says so:
  "Interactive demo. Not a live Mattermost recording." No
  AI-generated video was used (0 generative video).

## v2 — `~/workspace/bangsayur-demo-video-v2.mp4`
(2 min 5 s, 720×1558 portrait, h264 + AAC, 3.0 MB)

**What changed from v1:** v1 showed ONE shared chat for warga and
vendor. v2 shows the split introduced in commit `c5b2ffa`: the warga
chat (picker warga only, 4 chips — Pesan sayur, Daftar harga, Pesanan
saya, Tagihan saya) and the separate PIN-gated vendor dashboard at
`/vendor` (Menunggu ACC with ACC/Tolak buttons, rekap, tagihan belum
bayar, rute with "Berikutnya" + Tandai diantar, harga & stok). The
vendor PIN screen shows only dots (••••) — the PIN digits never
appear on screen. v1 file is kept untouched at
`~/workspace/bangsayur-demo-video.mp4`.

**Shots (10 + title):** title → Sari orders Rp58.000 in warga chat →
YA, menunggu ACC → vendor PIN screen → dashboard: Menunggu ACC #1
Bu Sari Rp58.000, rekap 0, stok Kangkung 30 / Cabai 8 (belum turun)
→ vendor ACC #1 → dashboard rekap 1 pesanan Rp58.000, stok 28/7 →
Budi orders Rp40.000, YA, ACC #2 → dashboard rekap 2 pesanan
omzet Rp98.000, tagihan belum bayar Rp98.000, lunas Rp0 → dashboard
rute: Berikutnya Pak Budi Jl. Melati No. 5, lalu Bu Sari No. 12 →
Ratna in warga chat sees only her own (0, Rp0) → closing:
"Residents order in chat. The vendor works in the dashboard."

**How it was built:** same honest method as v1. `mock_server.py`
was extended to serve the real `webapp/index.html` AND
`webapp/vendor.html` plus `/api/vendor/ringkasan` and
`/api/vendor/acc` (PIN-gated, 403 without/wrong PIN), all calling
the real SQLite tools. `drive_demo_v2.py` drove the flow and
verified **21/21 checks** from SQLite + the vendor API (Rp58.000 /
Rp40.000 / Rp98.000; stock Kangkung 30→28, Cabai 8→7, Telur 15→14,
Tempe 20→18, unchanged before ACC; route order; Ratna privacy).
`render_shots_v2.py` rendered the 11 frames with PIL following the
real layouts of `index.html` and `vendor.html`; narration is English
TTS, one voice (`avocado_v2:MAI_03`, speed 90), 10 clips, 99.1 s
total; subtitles burned in (PlayRes 720×1558, FontSize 34, 2 cues
per shot). `assemble_v2.py` built the video. Verification frames
extracted at 12 s (warga chat), 46 s (dashboard menunggu ACC),
93 s (route) — all readable, numbers correct, subtitles do not
cover the main content. Audio confirmed present (RMS −31.8 dB,
peak −5.8 dB). `python3 -m py_compile` passes for all new/changed
scripts. Working files: `/tmp/video-demo/` (`drive_demo_v2.py`,
`render_shots_v2.py`, `assemble_v2.py`, `transcript_v2.json`,
`shots-v2/`, `narr-v2/`, `subs-v2.srt`).

**What v2 is NOT (same as v1):** not a live LLM demo (Baseten
unavailable in the recording VM, credential 403), not live
Mattermost/Switch (web app, not a Mattermost group), frames are PIL
renders not browser screenshots (headless Chrome cannot start in
this VM), emoji stripped in renders. No AI-generated video was used
(0 generative video). A live phone re-recording is still the
strongest option before submitting (see "How Depa can re-record"
below); the two-room Switch flow is also still unproven live.

---

# VIDEO_NOTE.md — How the BangSayur demo video was made (v1)

Video file: `~/workspace/bangsayur-demo-video.mp4`
(1 min 50 s, 720×1558 portrait, h264 + AAC, 2.9 MB)

## What this video IS

A screen-style demo of the BangSayur web app, following
`demo/VIDEO_SCRIPT-EN.md` (9 shots) and `demo/transcript-demo-EN.md`.
The chat text is real: every agent reply was produced by the real
SQLite tools (`agent/tools.py` + `agent/agent.py` `_execute`, the same
enforcement/privacy path as `run_turn`), driven through a temporary
mock server. The numbers are the verified demo numbers:

- Bu Sari: 2 kangkung + 1 kg cabai merah = **Rp58.000**
- Pak Budi: 1 kg telur ayam + 2 tempe = **Rp40.000**
- Omzet hari ini: **Rp98.000**, lunas Rp0, belum bayar Rp98.000
- Stok turun hanya saat vendor ACC: Kangkung 30→28, Cabai merah 8→7,
  Telur ayam 15→14, Tempe 20→18
- Bu Ratna sees only her own data (0 orders, Rp0); the full route with
  addresses (Pak Budi Jl. Melati No. 5 first, then Bu Sari No. 12)
  is vendor-only.

Narration is English TTS (one voice, `avocado_v2:MAI_03`, speed 90),
with English subtitles burned in. The opening title card states the
limitation plainly.

## What this video is NOT — read this before submitting

- **Not a live LLM demo.** The live Baseten model was not available
  in the recording VM (the `custom.baseten` credential is rejected
  with 403 for this sandbox), so agent replies were composed from
  real SQLite tool results by a rule-based mock server — exactly the
  same data path as `demo/run_webapp_demo.py --mock` (22/22 checks).
- **Not live Mattermost / Switch.** The chat shown is the BangSayur
  web app (`webapp/index.html`), not a Mattermost group.
- **Not browser screenshots.** Headless Chrome in this VM cannot
  start: the Hatch build requires a browser-daemon WebGL policy
  (`Hatch WebGL domain policy is required for browser startup`);
  6+ CLI variants were tried and none produced any output file.
  The chat frames were therefore rendered deterministically with PIL,
  reproducing the web app's real layout (header #075e54, bubbles
  #dcf8c6 / white, chips, input bar, 390×844) with the exact bubble
  text from the mock transcript. Emoji are stripped in the render
  (DejaVu has no colour-emoji glyphs; the avatar leaf is a "B"
  initial) — the words are unchanged.
- **No AI-generated video was used** (0 generative video).

## How it was built (reproducible)

Working files live in `/tmp/video-demo/`:

- `mock_server.py` — serves the real unchanged `webapp/index.html`
  plus `/api/pelanggan`, `/api/harga`, `/api/chat` (rule-based,
  real SQLite tools, fresh temp DB, vendor PIN demo `1234`).
- `drive_demo.py` — drives the 9 scripted turns, verifies 13 checks
  against SQLite, writes `transcript.json`.
- `render_shots.py` — PIL renders of the 10 frames (title + 9 shots).
- `narr/shotN.txt` + `narr/shotN.mp3` — English narration, TTS.
- `assemble.py` — ffmpeg assembly (title 6 s + each shot held for
  narration + 2 s pad), subtitles from `subs.srt` (libass burn-in).
- `transcript.json`, `subs.srt`, `frames/` (verification thumbnails).

## How Depa can re-record a live version from a phone

1. Run the real app: `python3 -m webapp.server` (needs a PC or a
   server; on a phone, run it on a hosted machine and open the
   web app URL in the phone browser).
2. Set `BASETEN_API_KEY` in `.env` so the agent uses the live model,
   and have the Mattermost/Switch group open for the real group-chat
   version.
3. Follow `demo/VIDEO_SCRIPT-EN.md` shot by shot (same messages,
   same YA → ACC flow, PIN demo `1234`).
4. Record the phone screen with the built-in screen recorder while
   reading the English narration from `VIDEO_SCRIPT-EN.md`, or mute
   and add the same TTS narration afterwards.
5. Replace this file with the live recording before submitting — the
   judges' rubric gives 30% to "Use of Switch", so a live
   Switch/Mattermost recording is worth the effort.
