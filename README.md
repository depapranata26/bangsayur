# BangSayur — A Mobile Vegetable Vendor Agent in a Group Chat

**Flip the Switch Hackathon** (WeMakeDevs × DevTools Academy × Switch) —
Track 01: Best Business Workflow. Submissions close **Nov 8, 2026, 01:29 WIB**
(Nov 7, 23:59 IST).

Residents of a housing complex order vegetables in a group chat, and
**BangSayur** — an AI agent living in that group via
[Switch](https://github.com/sandbox-quantum/switch) — records orders, sums up
the daily total, plans delivery routes per block, chases unpaid bills, and
recaps revenue. Not a chatbot that only answers text: every answer comes
from a database (SQLite) through tool calls, so prices, totals, and stock
are never made up.

Agent brain: **Muse Spark** (`meta-models/muse-spark-open-1026`) via Baseten
(OpenAI-compatible endpoint). Language: Indonesian (the agent speaks
Indonesian with the residents; this README is in English for the judges).

> Indonesian version: [README-ID.md](README-ID.md)

## Proven working (live, Nov 5, 2026)

Full demo scenario in the Mattermost room **Warung Sayur - Komplek Melati**,
complete transcript in [`demo/transcript-demo.md`](demo/transcript-demo.md)
(English version with translations:
[`demo/transcript-demo-EN.md`](demo/transcript-demo-EN.md)):

| # | Resident | Agent | Result |
|---|----------|-------|--------|
| a | Bu Sari orders 2 bunches of kangkung + 1 kg red chili | `cari_pelanggan` → `catat_pesanan` | Order #1, Rp58,000, stock reduced |
| a | Pak Budi orders 1 kg eggs + 2 blocks of tempeh | `catat_pesanan` | Order #2, Rp40,000 |
| b | "total pesanan hari ini berapa?" ("today's total?") | `rekap_harian` | 2 orders, revenue Rp98,000 |
| c | "rute hari ini gimana?" ("today's route?") | `rute_hari_ini` | Block A, 2 stops, address-ordered |
| d | "siapa aja yang belum bayar?" ("who hasn't paid?") | `tagihan_belum_bayar` | 2 people, total Rp98,000 |
| e | "rekap omzet hari ini dong" ("today's revenue recap") | `rekap_omzet` | Revenue Rp98,000, paid Rp0 |

## Architecture

```
Residents (Mattermost, room #pesan-sayur) ──bridge──> Switch Core ──SSE──> agent/run.py (BANGSAYUR_ROLE=warga)
Vendor    (Mattermost, room #dapur-bangsayur) ──bridge──> Switch Core ──SSE──> agent/run.py (BANGSAYUR_ROLE=vendor)
                                                                                  │
                                                                     Muse Spark (Baseten)
                                                                                  │ tool calls
                                                                            SQLite (data/*.db)
```

**Two rooms, not one chat.** The vendor does NOT work in the residents'
chat: residents order in `#pesan-sayur` and only ever see their own
orders, while the vendor approves orders, reads recaps, plans routes
and chases bills in `#dapur-bangsayur` (vendor-only). A new order from
the residents' room appears in the vendor room as "waiting for ACC";
the vendor approves it there, and the agent then tells the resident in
the residents' room that the order is confirmed. One Switch connection
can only claim one room, so the two rooms are served by two runner
processes sharing the same DB and agent credentials (see step 4 below).
**Status: the two-room design and its supporting code exist, but it has
NOT been tested live against Switch/Mattermost yet** — do not claim a
live two-room demo until it has been run and proven.

- **Switch Core** — the open-source Switch server, running at
  `http://127.0.0.1:8000`. The room is bridged to Switch's built-in Mattermost
  channel.
- **`agent/run.py`** — runner: opens the SSE stream, 5s heartbeat,
  `connect_to_room`, listens for messages mentioning `@bangsayur`, runs the
  tool loop, replies via `post_message`.
- **`agent/agent.py`** — the brain: Muse Spark tool loop (native `tool_calls`
  + ```json block fallback), BangSayur persona, hard rule "prices/stock only
  from tools".
- **`agent/tools.py` + `agent/db.py`** — SQLite tools: `cari_pelanggan`
  (find customer), `daftar_harga` (price list), `catat_pesanan` (record
  order), `rekap_harian` (daily recap), `rute_hari_ini` (today's route),
  `tagihan_belum_bayar` (unpaid bills), `tandai_lunas` (mark paid),
  `rekap_omzet` (revenue recap), plus the safety/operations tools below.
  Seed: 20 vegetables (Medan prices) + 6 customers (Blocks A–D).
- **`agent/switch_client.py`** — stdlib-only Switch protocol client (urllib):
  agent registration, SSE events, heartbeat, ops.

## Web app (WhatsApp-style UI)

For residents who don't want to install a chat app: open a link, chat like
WhatsApp. `webapp/` — stdlib server on port 8001 + a single HTML file:

```bash
cd webapp
python3 server.py   # http://127.0.0.1:8001 — demo DB: data/webapp.db (fresh)
```

- **Residents' chat (`/`, `webapp/index.html`)** — green header + 🥬
  avatar + online status, "Saya:" ("I am:") picker with residents only
  (Bu Sari, Pak Budi, Bu Ratna, ... — no "Tukang Sayur" option),
  white/green bubbles + timestamps, quick-action chips for residents
  only (Order vegetables, Price list, My orders, My bills), typing
  indicator, and a "Dashboard Tukang Sayur →" link at the top. Totals,
  routes, revenue recaps and the waiting-ACC list are NOT in this chat
  — they belong to the vendor.
- **Vendor dashboard (`/vendor`, `webapp/vendor.html`)** — a separate,
  PIN-gated page for the vendor only: orders waiting for ACC (with ACC /
  Reject buttons), today's recap, unpaid bills (with Mark paid per
  order, method cash/transfer/QRIS), today's route in Block A→D order
  (with Mark delivered per stop and a "Next stop" card), price & stock
  editing, latest complaints, and shop open/closed status + order
  cutoff. It calls the real SQLite tools directly through
  `/api/vendor/*` endpoints (all PIN-gated, 403 without the right PIN);
  it does not go through the LLM. Open it at
  `http://127.0.0.1:8001/vendor` and enter the vendor PIN — demo PIN
  `1234` when `BANGSAYUR_VENDOR_PIN` is unset; set your own strong PIN
  with `BANGSAYUR_VENDOR_PIN=<your PIN>` before real use (the PIN is
  never shown in the page or in any log).
- The exact same agent backend (`agent.run_turn` + SQLite tools) — answers,
  prices, and stock are identical to the Switch/Mattermost demo.
- Verified 6/6 steps via `/api/chat` (Nov 5, 22:00): order #1 Rp58,000,
  #2 Rp40,000, recap Rp98,000, Block A route, unpaid Rp98,000, revenue
  paid Rp0.

## Safety system (anti fake orders)

An order never becomes final immediately — 4 layers:

1. **Known customers first** — new residents must register (name + block +
   address) via `daftar_pelanggan` before their order is recorded.
2. **Confirmation** — the agent repeats the summary + total; the order is
   only recorded after the resident replies YA ("yes").
3. **Vendor approval** — the order enters status `menunggu_acc`
   ("waiting for approval"); stock is only reduced and the order only
   enters recaps/routes/bills after the vendor approves
   (`konfirmasi_pesanan`, actions `acc`/`tolak` = approve/reject). Vendor
   commands only come from the vendor's own sender.

   Vendor identity: if `BANGSAYUR_VENDOR_IDS` is set (comma-separated
   Mattermost user IDs), only a sender whose ID is on that list counts as
   the vendor; a matching name alone is NOT enough. If the variable is
   empty (demo mode), the vendor is recognised by sender name only — that
   fallback is demo-only and unsafe for production, because anyone can
   pick that name. In the web app, vendor commands additionally require
   the `BANGSAYUR_VENDOR_PIN` (set your own strong PIN; if unset, demo
   mode accepts the demo PIN `1234`).
4. **Blacklist** — `tandai_tidak_diambil` (marked not picked up): stock is
   returned, the customer's no-show count +1; 2 no-shows → the customer is
   `ditahan` ("held"), and their next order enters `menunggu_dp`
   ("waiting for down payment") and only proceeds after the vendor confirms
   the DP arrived (`dp_masuk`).

Order status: `menunggu_acc` → `dikonfirmasi` ("confirmed") / `ditolak`
("rejected"); `menunggu_dp` → `menunggu_acc`; `dikonfirmasi` →
`tidak_diambil` ("not picked up"). Recaps/routes/bills/revenue ONLY count
`dikonfirmasi`; pending ones are listed separately. Old databases are
migrated automatically (`db._migrate`): old orders count as `dikonfirmasi`.

Verified end-to-end via the web app (Nov 5, 22:30): new resident →
register → YA → menunggu_acc → ACC → dikonfirmasi; reject; 2x not picked
up → held → DP → ACC. Stock returns to full after every not-picked-up.

## Routes (no backtracking)

`rute_hari_ini` sorts stops: Block A → B → C → D, and inside a block by
street then house number (`_parse_alamat`: "Jl. Melati No. 5" before
"No. 12"). Each stop carries `status_antar` ('belum'/'diantar' =
not-yet/delivered) plus `berikutnya` (the nearest undelivered stop).

- `tandai_diantar(pesanan_id)` — the vendor has arrived at a resident's
  house (confirmed orders only, vendor only).
- `rute_berikutnya()` — the next stop + remaining stops.
- Orders approved mid-route slot into the correct position immediately.

Verified end-to-end via the web app (Nov 5, 22:45): 3 orders (Sari,
Melati 12, ordered first) route as Budi Melati 5 → Sari Melati 12 →
Ratna Kenanga 8; "berikutnya" ("next") → Budi; "sudah diantar #2"
("delivered #2") → next becomes Sari; late order Dewi (Block C) slots in
last.

## Everything else (all built Nov 5, 22:50–23:00)

- **Daily prices/stock** — `atur_harga_stok` (vendor only): "cabai merah
  naik 55 ribu, stok kangkung 20" ("red chili up to 55 thousand, kangkung
  stock 20"). Prices in `daftar_harga` are the same for every resident.
- **Resident shorthand** — aliases in `_cari_item`: bamer, baput, cabe,
  rawit, telor, etc. resolve straight to the item.
- **Edit/cancel** — `ubah_pesanan` / `batalkan_pesanan` for orders still
  waiting for approval (owner name must match; nobody can cancel someone
  else's order). The agent also merges a follow-up order into a still
  pending one when the resident agrees.
- **Complaints** — `catat_komplain` + `daftar_komplain` (vendor).
- **Payments** — `tandai_lunas(pesanan_id, metode)` (cash/transfer/QRIS,
  vendor only); a resident's `lapor_bayar` ("I already transferred")
  becomes status "lapor transfer" and does NOT auto-mark as paid until
  verified; `tandai_bon` + due date (stays in the bills);
  `hitung_kembalian` (change calculator).
- **Drop-offs** — `tambah_catatan` ("titip ke Bu Sari" = "leave it with
  Bu Sari") shows up in the route.
- **Closed days & order cutoff** — `atur_status_toko` (open/closed + a
  message); when closed, new orders are refused with the vendor's message.
  `atur_cutoff` (default 07:00): orders after that hour are automatically
  dated tomorrow (`untuk_besok=true`).
- **Privacy** — another resident's address/phone is never mentioned to a
  resident; the full route is vendor-only. Vendor commands are enforced in
  `_execute` (not just in the prompt): a resident asking for ACC / mark
  paid / change prices is rejected by the system.
- **Backup & cost** — `buat_backup` (full JSON to data/backup-*),
  `cek_biaya` (calls + tokens per day; no Rupiah price shown because rates
  change). Tokens are logged automatically on every model reply.

Verified end-to-end via the web app (Nov 5, 22:57): price update, edit,
complaint, report payment → mark paid, IOU, drop-off, closed day →
order refused, reopen, backup, cost (54 calls / 302,380 tokens).

NOTE: an old web server once kept serving after a restart (kill-by-PID hit
its own shell) — kill by PORT (`fuser -k 8001/tcp`) and verify the new PID
before testing.

## How to run (reproduce the demo)

### 0. Prerequisites

- Python 3.12+ (`pip install -r requirements.txt` — only `httpx`, for demo scripts;
  the agent + webapp themselves use only the stdlib), PostgreSQL 16,
  Node.js 20+ (for Switch Console, optional)
- `BASENTEN_API_KEY` — Baseten API key for the Muse Spark model
  (or a Secure Vault integration; the key is **never** written in the repo)
- Switch repo: `git clone https://github.com/sandbox-quantum/switch` to
  `../switch-src` next to this repo, or set `SWITCH_SRC` to its path.
  Likewise set `BANGSAYUR_HOME` if this repo lives elsewhere; all
  scripts resolve paths relative to the repo root by default.

### 1. Switch Core + PostgreSQL

```bash
# PostgreSQL: database + roles for Switch (see switch-src/.env.example)
sudo -u postgres psql -c "CREATE DATABASE switch;" \
  -c "CREATE ROLE switch_app LOGIN PASSWORD '...';" \
  -c "CREATE ROLE postgres LOGIN PASSWORD '...';"  # owner, match .env

# Switch .env from the example + generate secrets:
#   cp switch-src/.env.example switch-src/.env
#   bash switch-src/deploy/local/generate-env-secrets.sh.env local
#   then fill in DB_PASSWORD / DB_OWNER_PASSWORD

# Run the core (this script loads .env — plain `uv run` does NOT):
bash demo/start_switch.sh
curl -s http://127.0.0.1:8000/health   # {"status":"ok"}
```

### 2. Mattermost + bridge

```bash
# Mattermost Team Edition (binary) + `mattermost` database, on :8065.
# Then register the bridge + create the demo team/users:
bash demo/setup_bridge.sh
# This script uses deploy/shared_resources/setup.py from the Switch repo:
# it creates team `komplek-melati`, users `pemilik`/`warga`, and registers
# the Mattermost bridge as the default. Enable bot creation in
# Mattermost first (ServiceSettings.EnableBotAccountCreation=true) —
# otherwise the agent bot fails to be created ("Bot creation has been
# disabled").
```

### 3. Register the BangSayur agent

```bash
cd agent
python3 -c "
from switch_client import SwitchClient
import os
print(SwitchClient.register('http://127.0.0.1:8000', 'bangsayur',
      'Agen tukang sayur keliling untuk warga komplek',
      os.environ['AGENT_REGISTRATION_TOKEN']))"
# Save {id, api_key} to .switch-agent.json in the repo root
# (chmod 600, GITIGNORED; override with SWITCH_CREDS_FILE).
# Then open the agent's addressing policy to all residents:
python3 ../demo/open_addressing.py   # PUT {"policy": null} as admin
# (see demo/open_addressing.py — the agent cannot change its own setting)
```

### 4. Run the runner + demo scenario

```bash
cd agent
python3 run.py            # uses .switch-agent.json + .room.json (creates a
                          # new room if none exists); listens to the room,
                          # answers @bangsayur mentions
# In another terminal, send the scenario as simulated residents:
python3 ../demo/run_scenario.py
# Transcript + DB verification: demo/transcript-demo.md
```

Two rooms need two runners (same DB, same agent credentials):

```bash
BANGSAYUR_ROLE=warga  python3 run.py   # room #pesan-sayur (.room.json)
BANGSAYUR_ROLE=vendor python3 run.py   # room #dapur-bangsayur (.vendor-room.json)
# Override the vendor room with SWITCH_VENDOR_ROOM_ID=... /
# BANGSAYUR_VENDOR_ROOM_ID=... (file: SWITCH_VENDOR_ROOM_FILE).
```

Reset the demo anytime (from the repo root): `rm data/bangsayur.db .room.json .vendor-room.json`,
then repeat step 4 (the runner creates new rooms + Mattermost channels).
`.room.json`, `.vendor-room.json` and `.switch-agent.json` all live in
the repo root (override with `SWITCH_ROOM_FILE` / `SWITCH_VENDOR_ROOM_FILE` /
`SWITCH_CREDS_FILE`).

## Implementation notes (traps already passed)

- **Ops need an open connection:** the SSE stream must be opened FIRST
  before any `op()`, otherwise the server answers 409 "connection is not
  open".
- **`post_message` without `room_id`:** the message goes to the room
  claimed by the connection via `connect_to_room`.
- **Default addressing `owner_only`:** non-owner residents mentioning the
  agent get rejected ("I only take instructions from my owner..."). Open it
  via `PUT /gateway/agents/{id}/addressing-policy` with `{"policy": null}`
  (the agent cannot change its own setting — an admin/owner must).
- **Mattermost bots are created at core startup:** an agent registered
  AFTER the core is running doesn't get a bot right away — restart the core
  so identities get provisioned ("Provisioned mattermost identities for N
  agents"), and make sure bot creation is enabled in the Mattermost config.
- **The bot must be a channel member:** a room created before the bot
  existed doesn't contain the bot — add it manually via the Mattermost API,
  or create a new room after the bot exists.
- **The bridge admin account (`pemilik`) cannot talk to the agent:** the
  Switch adapter deliberately ignores posts from its own admin user. For the
  demo, the revenue question comes from the `warga` (vendor) account.
- **Proxy egress:** Baseten calls MUST go through the VM's HTTP(S) proxy —
  don't unset the proxy env in the runner (the `hsurr:*` surrogate token is
  only swapped by Sentinel on the proxy path; without the proxy Baseten
  answers 401). Conversely, `httpx` breaks on the IPv6-bracket entry in
  `NO_PROXY` — unset the proxy only in scripts that use httpx
  (setup/probe), not in the runner.
- **Customer name vs username:** chat username `busari` = customer
  `Bu Sari` — `cari_pelanggan` normalizes spaces on both sides.
- **`just run` loads `.env`, `uv run` doesn't** — and `just` isn't on every
  VM; `demo/start_switch.sh` loads `.env` manually.

## Repo structure

```
bangsayur/
├── README.md           # this file (English)
├── README-ID.md        # Indonesian version
├── SUBMISSION.md       # ready-to-paste hackathon submission text (English + Indonesian meaning)
├── docker-compose.yml      # Switch + Mattermost + Postgres (needs Docker; UNTESTED — see header in the file, bare-metal steps above are the verified path)
├── .env.example            # example env, NO secrets
├── .gitignore              # .switch-agent.json, .env, *.db, venv/, __pycache__/
├── agent/
│   ├── agent.py            # brain: Muse Spark tool loop (Baseten)
│   ├── tools.py            # SQLite tools (prices/orders/routes/bills/revenue)
│   ├── db.py               # schema + seed (20 items, 6 customers, Blocks A-D)
│   ├── switch_client.py    # Switch protocol client (stdlib-only)
│   └── run.py              # runner: SSE + heartbeat + answer mentions
├── webapp/
│   ├── server.py           # WhatsApp-style web chat server (port 8001)
│   ├── index.html          # single-file WA-style UI (residents only)
│   └── vendor.html         # vendor dashboard (PIN-gated, /vendor)
├── tests/
│   ├── test_tools.py       # unittest (stdlib only): orders, privacy, money, race
│   └── test_vendor_dashboard.py  # unittest: vendor PIN gate, vendor endpoints, split views
├── docker/
│   └── postgres-init/01-mattermost.sh   # create mmuser + mattermost DB
└── demo/
    ├── start_switch.sh     # run switch-core (loads .env)
    ├── setup_bridge.sh     # Mattermost + Switch bridge registration
    ├── run_scenario.py     # send the 6-step demo as residents
    ├── probe_room.py       # one-off probe (stream/room/event)
    ├── transcript-demo.md  # demo transcript (YA→ACC, verified via local simulation)
    ├── transcript-demo-EN.md  # English version, agent replies in original Indonesian + translation
    ├── transcript-webapp.md  # output of run_webapp_demo.py --mock
    ├── transcript-webapp-EN.md  # English version of the webapp transcript (22 checks)
    ├── run_webapp_demo.py  # re-run the 6-step demo, --mock or --live
    ├── VIDEO_SCRIPT.md     # shot-by-shot script for the <3 min demo video
    └── VIDEO_SCRIPT-EN.md  # bilingual English/Indonesian version of the video script
```

## Demo video (not recorded yet)

**Status: NOT RECORDED.** Follow the shot-by-shot script in
`demo/VIDEO_SCRIPT.md` (9 shots, 2 min 58 sec, recorded from a phone;
bilingual English version: `demo/VIDEO_SCRIPT-EN.md`). Ready-to-paste
submission text is in [`SUBMISSION.md`](SUBMISSION.md):
Bu Sari orders → summary + YA → waiting for ACC → vendor ACC → stock
drops; Pak Budi the same way; Bu Ratna asks for her recap (only her own,
0); the vendor asks for revenue Rp98,000 and the route (Pak Budi
Jl. Melati No. 5 first, then Bu Sari No. 12).

The video is recorded from the **web app in a phone browser** (WhatsApp-
style chat), NOT from live Mattermost. Do not claim it is a live
Mattermost recording until a real live recording exists. The matching
transcript is `demo/transcript-demo.md` — it is **not a live Mattermost
log**; it was verified via local simulation
(`python3 demo/run_webapp_demo.py --mock`, 22 checks). Re-run it with:

```bash
python3 demo/run_webapp_demo.py --mock   # no model, no Switch/Mattermost
python3 demo/run_webapp_demo.py --live [--vendor-pin <PIN>]  # needs Baseten
```

## Why Switch is central (and the web app is only an alternative)

- **Switch + Mattermost is the main path**, because that is where the
  residents' group chat lives: the residents' room (`#pesan-sayur`) plus
  the vendor-only room (`#dapur-bangsayur`), the agent answers
  `@bangsayur` mentions, and the sender identity comes from each
  person's Mattermost account. Every flow (order → YA → ACC → route →
  bills) was designed for those rooms — residents never see the
  vendor's recap, route or bills, and the vendor never works inside
  the residents' chat.
- **The web app (`webapp/server.py`) is only an alternative door / demo
  tool.** It runs the SAME agent (`agent.run_turn`, same SQLite tools),
  but: (1) one user at a time — the sender is picked from the "Saya"
  picker, not from a real chat account; (2) its DB is separate
  (`data/webapp.db`, not `data/bangsayur.db`); (3) there is no room/group,
  so multi-resident dynamics are only simulated. It is useful for a
  phone demo and quick tests without running Switch/Mattermost — not a
  replacement for the main path.

## Tests

```bash
python3 -m py_compile agent/*.py webapp/server.py demo/*.py tests/*.py
python3 -m unittest discover -s tests -v
```

`tests/test_tools.py` (unittest, stdlib only, temp DBs in /tmp) covers:
order → ACC reduces stock exactly once, second ACC rejected, scoped
privacy (a resident only sees their own recap/bills/order, address
redacted), another resident's order cannot be edited, notes append,
exact change with decimals, address parsing variants, a two-thread
stock race that must not oversell, `run_turn` out of iterations replying
with an apology instead of raw JSON, WIB (`Asia/Jakarta`), and the
vendor-ID check.
`tests/test_vendor_dashboard.py` covers the split: vendor endpoints
without/with the wrong PIN return 403 and leak no data, ACC through the
endpoint reduces stock exactly once, Mark delivered only works for
confirmed orders, price changes need the vendor PIN, and the residents'
chat contains no vendor chips or vendor picker option while
`/vendor` is PIN-gated and shows no PIN value in its HTML.

## Known limitations

- **Demo video not recorded yet** (see above); the transcript is verified
  via local simulation, not a live log. Note: the video script
  (`demo/VIDEO_SCRIPT.md`, `demo/VIDEO_SCRIPT-EN.md`) was written BEFORE
  the resident/vendor split — it shows the old single-chat flow. The
  split (residents' chat + vendor dashboard, two Switch rooms) is the
  current design; re-record the video following the split, do not
  present the old script as the current flow.
- **Two Switch rooms are not tested live yet.** The design, the
  `BANGSAYUR_ROLE` runner support and the `resolve_vendor_room_id`
  helper exist and are documented, but no live Mattermost/Switch run
  has proven the two-room flow end to end.
- **Live demo script mode (`--live`) has not been run** in this session
  (no Baseten call was made); only `--mock` (22 checks) is verified.
  Run `--live` once before claiming an end-to-end web-app flow with the
  model.
- **Vendor auth:** with `BANGSAYUR_VENDOR_IDS` set, the vendor is
  recognised by user ID; with it empty (demo mode), by sender NAME only
  — names can be faked by anyone, so demo mode must NOT be used in
  production. In the web app, vendor commands are also gated by
  `BANGSAYUR_VENDOR_PIN` (empty = demo mode, demo PIN `1234` accepted).
  Set a strong PIN of your own before real use; never commit a filled
  `.env`.
- **Cutoff:** orders after 07:00 WIB automatically become TOMORROW's
  orders (`untuk_besok=true`). The demo script reads the order date from
  the DB so recaps/routes still match even when run after the cutoff.
- **`docker-compose.yml` is still UNTESTED.** The file is valid YAML
  (`python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"`
  → OK), but there is no Docker in the development VM, so it has never
  run end-to-end. Do not use compose as the main reproduction path; the
  verified path is the bare-metal steps above.
- **Stock race and SSE reconnect are fixed in code and covered by local
  tests** (transactions with `BEGIN IMMEDIATE`; reconnect with backoff
  2/5/10/30 s, max 5 attempts; model retry only for 429/500/502/503),
  but neither has been proven against live Switch/Mattermost yet.

## What is NOT committed

`.env`, `.switch-agent.json` (agent api_key), `.room.json`,
`.vendor-room.json`, `*.db`,
`demo/venv/`, `__pycache__/`. The demo Mattermost passwords (`warga-pw`,
`pemilik-pw`) are for the local demo environment only — change them in a
real deployment.
