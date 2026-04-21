"""
civiclaw audit log — cryptographic append-only log designed to produce
EU AI Act Article 12-compliant records.

Each entry is a JSON line containing:
  - ts                ISO-8601 UTC timestamp
  - actor             who or what performed the action (skill name, human ID)
  - skill             skill that emitted the event
  - event             dotted event name (intake.parsed, response.drafted, ...)
  - ref               reference to the artefact (request ID, document hash)
  - data              arbitrary payload, JSON-serialisable
  - prev_hash         SHA-256 of the previous record (hex)
  - hash              SHA-256 of (prev_hash + canonical payload)

The hash chain makes tampering detectable: remove or edit any entry and the
chain breaks at every subsequent record.

Write-only. No delete path. No edit path. Design constraint, not a bug.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLog:
    """Append-only, hash-chained audit log.

    File layout: one JSON object per line. Read with:
        for line in open(path):
            entry = json.loads(line)
    """

    GENESIS_HASH = "0" * 64

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch(mode=0o640)

    def _last_hash(self) -> str:
        if self.path.stat().st_size == 0:
            return self.GENESIS_HASH
        with self.path.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            # Walk backwards to find the last newline
            pos = size - 1
            while pos >= 0:
                fh.seek(pos)
                if fh.read(1) == b"\n":
                    if pos == size - 1:
                        pos -= 1
                        continue
                    fh.seek(pos + 1)
                    break
                pos -= 1
            else:
                fh.seek(0)
            last = fh.read().decode("utf-8").strip()
        if not last:
            return self.GENESIS_HASH
        return json.loads(last).get("hash", self.GENESIS_HASH)

    def _hash(self, prev_hash: str, payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256((prev_hash + canonical).encode("utf-8")).hexdigest()

    def append(
        self,
        *,
        actor: str,
        skill: str,
        event: str,
        ref: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        prev_hash = self._last_hash()
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "skill": skill,
            "event": event,
            "ref": ref,
            "data": data or {},
            "prev_hash": prev_hash,
        }
        payload["hash"] = self._hash(prev_hash, payload)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, separators=(",", ":")) + "\n")
        return payload

    def verify(self) -> tuple[bool, int, str | None]:
        """Walk the log and verify the hash chain.

        Returns (ok, lines_checked, error).
        """
        prev_hash = self.GENESIS_HASH
        lines = 0
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                lines += 1
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as exc:
                    return False, lines, f"invalid JSON on line {lines}: {exc}"
                if entry.get("prev_hash") != prev_hash:
                    return False, lines, f"prev_hash mismatch on line {lines}"
                payload_for_hash = {k: v for k, v in entry.items() if k != "hash"}
                expected = self._hash(entry["prev_hash"], payload_for_hash)
                if entry.get("hash") != expected:
                    return False, lines, f"hash mismatch on line {lines}"
                prev_hash = entry["hash"]
        return True, lines, None


if __name__ == "__main__":
    # Tiny smoke test.
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tf:
        log = AuditLog(tf.name)
        log.append(actor="alfred", skill="dsar", event="intake.parsed", ref="REQ001",
                   data={"requester": "S. Wilson", "subject": "J. Wilson"})
        log.append(actor="alfred", skill="dsar", event="search.planned", ref="REQ001",
                   data={"sources": ["SIS", "SCSS", "EHCP"]})
        log.append(actor="alfred", skill="dsar", event="response.drafted", ref="REQ001",
                   data={"words": 412})
        ok, n, err = log.verify()
        print(f"verified: {ok}, entries: {n}, error: {err}")
