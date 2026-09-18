"""Append-only audit trail.

Constraint 5: every turn, consent event and disposition is logged and correlatable across bot,
dialer, CRM and SBI Card systems, and logs are append-only.

Append-only is enforced here by only ever opening with mode "a" and never exposing an update or
delete. That is not tamper-proofing - a filesystem is not a WORM store - and the production
version needs object-lock storage with a retention policy covering the 3-year archive, inside
India. What this does give is a format that cannot be silently rewritten by our own code, which
is the failure mode we control.

Two streams, because they answer different questions and have different retention:

  turns.jsonl   one row per turn. What was heard, what was chosen, what was said, how long it
                took. This is the evidence for script-adherence scoring (RESEARCH 2.6) and it
                is what an auditor reads when asking "did the bot disclose the rate".
  calls.jsonl   one row per call. The handoff payload plus the advisor outcome. This is what
                the cost-per-booked-SR report is computed from.

Correlation id is on every row in both, and it is the same id we hand the partner at transfer.
"""

from __future__ import annotations

import json
import pathlib
import threading
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_DIR = ROOT / "runs"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Audit:
    def __init__(self, run_id: str, directory=None, append_ok: bool = True):
        self.dir = pathlib.Path(directory or DEFAULT_DIR) / run_id
        # Append-only is right for the log and wrong for a run id. Reusing one silently merges
        # two campaigns into one file and every metric downstream is computed across both -
        # which is how a stale 433-row slice showed up at exactly 100% connect. Writers must opt
        # out of appending; readers still open freely.
        if not append_ok and (self.dir / "calls.jsonl").exists():
            raise FileExistsError(
                f"run {run_id!r} already has an audit trail at {self.dir}. Appending would mix "
                f"two campaigns. Use a new --run-id, or delete the directory deliberately.")
        self.dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self._lock = threading.Lock()          # ponytail: one lock for both streams; split per
                                               # stream only if append contention shows up
        self.turns_path = self.dir / "turns.jsonl"
        self.calls_path = self.dir / "calls.jsonl"

    def _append(self, path: pathlib.Path, row: dict):
        line = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def run_header(self, meta: dict):
        self._append(self.calls_path, {"ts": _now(), "type": "run", "run_id": self.run_id, **meta})

    def turn(self, correlation_id: str, content_hash: str, rec, product: str, locale: str):
        self._append(self.turns_path, {
            "ts": _now(),
            "correlation_id": correlation_id,
            "content_hash": content_hash,
            "product": product,
            "locale": locale,
            "turn": rec.index,
            "heard": rec.utterance,
            "route_kind": rec.route_kind,
            "route_id": rec.route_id,
            "confidence": rec.confidence,
            "band": rec.band,
            "node_before": rec.node_before,
            "node_after": rec.node_after,
            # ids, not text: the words are reconstructable from the pack at content_hash, and
            # storing them twice means two things to keep in sync and two things to redact.
            "spoke": [[kind, ident] for kind, ident, *_ in rec.spoke],
            "router_ms": rec.router_ms,
            "policy_ms": rec.policy_ms,
        })

    def call(self, payload: dict, advisor_inbound: dict | None, extra: dict | None = None):
        self._append(self.calls_path, {
            "ts": _now(), "type": "call",
            **payload,
            "advisor": advisor_inbound,
            **(extra or {}),
        })

    def read_calls(self) -> list:
        if not self.calls_path.exists():
            return []
        rows = [json.loads(line) for line in
                self.calls_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return [r for r in rows if r.get("type") == "call"]

    def read_turns(self) -> list:
        if not self.turns_path.exists():
            return []
        return [json.loads(line) for line in
                self.turns_path.read_text(encoding="utf-8").splitlines() if line.strip()]
