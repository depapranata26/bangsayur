# VIDEO_NOTE.md — How the BangSayur demo video was made

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
