#!/usr/bin/env python3
"""Switch agent-protocol client (stdlib only): SSE events + heartbeat + ops.

Protokol: docs/old/api/AGENT_PROTOCOL.md di repo Switch.
- Registrasi: POST /agents (Bearer registration key) -> {id, api_key}
- Stream: GET /agents/{id}/events?connection_id=..&scope=all&filter=all (SSE)
- Heartbeat: POST /agents/{id}/connection/beat tiap 2 detik
- Operasi: POST /agents/{id}/ops/{operation} + header X-Switch-Connection-Id

Filter sengaja `all` (bukan `addressed`): addressing policy server hanya
mengizinkan owner, sementara warga demo adalah akun lain. Klien menyaring
sendiri: balas hanya pesan yang me-mention @bangsayur atau DM.
"""
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


class SwitchError(RuntimeError):
    pass


class SwitchClient:
    def __init__(self, base_url, agent_id, api_key):
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self.api_key = api_key
        self.connection_id = str(uuid.uuid4())
        self.cursor = 0
        self._stop = threading.Event()

    # -- low-level HTTP -----------------------------------------------------
    def _req(self, method, path, body=None, headers=None, timeout=30):
        url = self.base_url + path
        data = json.dumps(body).encode("utf-8") if body is not None else None
        h = {"Authorization": f"Bearer {self.api_key}",
             "Content-Type": "application/json"}
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, data=data, method=method, headers=h)
        try:
            with urllib.request.build_opener().open(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:800]
            raise SwitchError(f"{method} {path} -> HTTP {exc.code}: {detail}") from exc

    @staticmethod
    def register(base_url, name, description, registration_token):
        """Daftarkan agent baru. Kembalikan (agent_id, api_key)."""
        url = base_url.rstrip("/") + "/agents"
        body = {
            "name": name,
            "description": description,
            "connector_type": "custom-python",
            "integration_profile": {
                "connection_model": "always_on",
                "message_exchange": True,
                "pre_invocation_mediation": [],
                "post_invocation_mediation": [],
                "event_reporting": [],
            },
        }
        req = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"Authorization": f"Bearer {registration_token}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.build_opener().open(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:800]
            raise SwitchError(
                f"POST /agents -> HTTP {exc.code}: {detail}") from exc

    # -- ops -----------------------------------------------------------------
    def list_ops(self):
        return self._req("GET", f"/agents/{self.agent_id}/ops")

    def op(self, operation, args=None):
        return self._req(
            "POST", f"/agents/{self.agent_id}/ops/{operation}",
            body=args or {},
            headers={"X-Switch-Connection-Id": self.connection_id})

    # -- heartbeat -----------------------------------------------------------
    def beat(self):
        return self._req(
            "POST", f"/agents/{self.agent_id}/connection/beat",
            body={"connection_id": self.connection_id,
                  "cursor": self.cursor})

    def start_heartbeat(self, interval=2.0):
        def loop():
            while not self._stop.is_set():
                try:
                    self.beat()
                except Exception as exc:  # noqa: BLE001 - heartbeat tak boleh mati
                    print(f"[switch] heartbeat gagal: {exc}", flush=True)
                self._stop.wait(interval)
        t = threading.Thread(target=loop, daemon=True, name="heartbeat")
        t.start()
        return t

    def stop(self):
        self._stop.set()

    # -- SSE stream ----------------------------------------------------------
    def events(self):
        """Generator event SSE: yield dict {seq, type, data}."""
        qs = urllib.parse.urlencode({
            "connection_id": self.connection_id,
            "scope": "all",
            "filter": "all",
            "start_from": "head",
            "client": "bangsayur",
            "client_version": "0.1.0",
        })
        url = (f"{self.base_url}/agents/{self.agent_id}/events?{qs}")
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {self.api_key}",
                          "Accept": "text/event-stream"})
        resp = urllib.request.build_opener().open(req, timeout=None)
        seq, ev_type, data_lines = None, None, []
        try:
            while not self._stop.is_set():
                line = resp.readline().decode("utf-8", "replace")
                if line == "":
                    break  # stream putus
                line = line.rstrip("\n")
                if line == "":
                    if data_lines:
                        raw = "\n".join(data_lines)
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            data = {"_raw": raw}
                        if seq is not None:
                            try:
                                self.cursor = int(seq)
                            except ValueError:
                                pass
                        yield {"seq": seq, "type": ev_type, "data": data}
                    seq, ev_type, data_lines = None, None, []
                    continue
                if line.startswith(":"):
                    continue  # komentar/keepalive
                if line.startswith("id:"):
                    seq = line[3:].strip()
                elif line.startswith("event:"):
                    ev_type = line[6:].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
        finally:
            resp.close()
