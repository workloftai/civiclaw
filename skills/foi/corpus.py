"""
civiclaw FOI corpus interaction — direct agent tools over a council document
corpus, with no embedding model and no vector store.

Implements the architectural pattern from Li et al. (2026), "Beyond Semantic
Similarity: Rethinking Retrieval for Agentic Search via Direct Corpus
Interaction" (arXiv:2605.05242), framed for UK Local Authority FOI / DSAR
work.

Design rationale (the regulated-buyer version):

  Embedding-based retrieval requires copying the source corpus into a vector
  store. Under UK GDPR the vector store is itself a personal-data processing
  system: re-identifiable, hard to delete from, and a fresh data subject
  rights surface. Direct corpus interaction reads the source documents
  in-place. No copy, no embedding model, no vector store, no third-party
  inference call for the retrieval step.

  Trade-off: the agent makes more tool calls (multiple greps + reads instead
  of a single top-k retrieval). Acceptable, because each call is logged in
  the civiclaw audit chain and the regulator's evidence requirement is
  traceability, not throughput.

Tools exposed (each writes to the audit log):
  - Corpus.list(subpath="")        — directory listing
  - Corpus.grep(pattern, subpath)  — regex over raw bytes
  - Corpus.read(path, lo=None, hi=None) — read a file or a line range
  - Corpus.snippet(path, line_no, n=4)  — small context window around a hit

Constraints enforced:
  - Path traversal blocked (no `..` escapes outside corpus root)
  - Reads cap at MAX_READ_BYTES per call
  - Allowed file extensions configurable

This module is import-safe with no third-party deps. The agent loop that
drives these tools lives in skill.py:cmd_corpus_search.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from core.audit import AuditLog


DEFAULT_TEXT_EXTS = (".txt", ".md", ".rst", ".csv", ".tsv", ".log",
                     ".html", ".htm", ".xml", ".json", ".eml")
MAX_READ_BYTES = 64 * 1024
MAX_GREP_HITS = 200


@dataclass
class GrepHit:
    path: str
    line_no: int
    line: str


class CorpusError(Exception):
    """Raised when a tool call would violate the corpus contract."""


class Corpus:
    """Direct-access tool layer over a council document corpus root.

    Every public method appends one entry to the audit log. The audit log is
    therefore a complete record of which documents the agent inspected to
    produce a given FOI / DSAR response — the EU AI Act Article 12 evidence
    requirement, satisfied by construction.
    """

    def __init__(
        self,
        root: str | Path,
        audit: AuditLog,
        *,
        actor: str = "civiclaw.foi.corpus",
        ref: str | None = None,
        allowed_exts: Iterable[str] = DEFAULT_TEXT_EXTS,
    ) -> None:
        self.root = Path(root).resolve()
        if not self.root.exists() or not self.root.is_dir():
            raise CorpusError(f"corpus root not found or not a directory: {self.root}")
        self.audit = audit
        self.actor = actor
        self.ref = ref or "unspecified"
        self.allowed_exts = tuple(e.lower() for e in allowed_exts)

    # ------------------------------------------------------------------
    # Path safety
    # ------------------------------------------------------------------
    def _resolve(self, subpath: str) -> Path:
        target = (self.root / subpath).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise CorpusError(f"path escapes corpus root: {subpath}") from exc
        return target

    def _allowed(self, path: Path) -> bool:
        return path.suffix.lower() in self.allowed_exts

    def _rel(self, path: Path) -> str:
        return str(path.relative_to(self.root))

    # ------------------------------------------------------------------
    # Tool: list
    # ------------------------------------------------------------------
    def list(self, subpath: str = "") -> list[str]:
        """List allowed files under subpath, recursively."""
        target = self._resolve(subpath)
        if target.is_file():
            return [self._rel(target)] if self._allowed(target) else []
        out: list[str] = []
        for p in sorted(target.rglob("*")):
            if p.is_file() and self._allowed(p):
                out.append(self._rel(p))
        self.audit.append(
            actor=self.actor, skill="foi", event="corpus.list", ref=self.ref,
            data={"subpath": subpath, "count": len(out)},
        )
        return out

    # ------------------------------------------------------------------
    # Tool: grep
    # ------------------------------------------------------------------
    def grep(self, pattern: str, subpath: str = "", *, ignore_case: bool = True) -> list[GrepHit]:
        """Regex search over allowed files under subpath.

        Returns at most MAX_GREP_HITS hits; the agent should narrow the
        pattern or subpath if it hits the cap.
        """
        target = self._resolve(subpath)
        files: list[Path]
        if target.is_file():
            files = [target] if self._allowed(target) else []
        else:
            files = [p for p in sorted(target.rglob("*")) if p.is_file() and self._allowed(p)]

        flags = re.IGNORECASE if ignore_case else 0
        try:
            rx = re.compile(pattern, flags)
        except re.error as exc:
            raise CorpusError(f"invalid regex: {exc}") from exc

        hits: list[GrepHit] = []
        for f in files:
            try:
                with f.open("r", encoding="utf-8", errors="replace") as fh:
                    for i, line in enumerate(fh, start=1):
                        if rx.search(line):
                            hits.append(GrepHit(self._rel(f), i, line.rstrip("\n")))
                            if len(hits) >= MAX_GREP_HITS:
                                break
            except OSError:
                continue
            if len(hits) >= MAX_GREP_HITS:
                break

        self.audit.append(
            actor=self.actor, skill="foi", event="corpus.grep", ref=self.ref,
            data={
                "pattern": pattern, "subpath": subpath,
                "ignore_case": ignore_case, "hits": len(hits),
                "capped": len(hits) >= MAX_GREP_HITS,
            },
        )
        return hits

    # ------------------------------------------------------------------
    # Tool: read
    # ------------------------------------------------------------------
    def read(self, path: str, lo: int | None = None, hi: int | None = None) -> str:
        """Read a file, optionally a 1-indexed inclusive line range."""
        target = self._resolve(path)
        if not target.is_file():
            raise CorpusError(f"not a file: {path}")
        if not self._allowed(target):
            raise CorpusError(f"file extension not in allow-list: {path}")

        with target.open("r", encoding="utf-8", errors="replace") as fh:
            if lo is None and hi is None:
                data = fh.read(MAX_READ_BYTES + 1)
                truncated = len(data) > MAX_READ_BYTES
                body = data[:MAX_READ_BYTES]
            else:
                lines = fh.readlines()
                lo_idx = max(1, lo or 1)
                hi_idx = min(len(lines), hi if hi is not None else len(lines))
                body = "".join(lines[lo_idx - 1: hi_idx])
                truncated = False

        self.audit.append(
            actor=self.actor, skill="foi", event="corpus.read", ref=self.ref,
            data={"path": self._rel(target), "lo": lo, "hi": hi, "bytes": len(body), "truncated": truncated},
        )
        return body

    # ------------------------------------------------------------------
    # Tool: snippet
    # ------------------------------------------------------------------
    def snippet(self, path: str, line_no: int, n: int = 4) -> str:
        """Read n lines either side of line_no for verification context."""
        if line_no < 1:
            raise CorpusError("line_no must be >= 1")
        if n < 0:
            raise CorpusError("n must be >= 0")
        return self.read(path, lo=max(1, line_no - n), hi=line_no + n)
