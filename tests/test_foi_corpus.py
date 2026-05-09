"""
Tests for civiclaw.skills.foi.corpus — direct corpus interaction tool layer.

Run from repo root:
    python3 -m unittest tests.test_foi_corpus -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "skills" / "foi"))

from core.audit import AuditLog
from skills.foi.corpus import Corpus, CorpusError


class CorpusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "minutes").mkdir()
        (self.root / "minutes" / "2026-03-cabinet.md").write_text(
            "Cabinet 12 March 2026\n"
            "Item 4: SEND budget reallocation £2.4m to Aspire Trust\n"
            "Item 5: agreed.\n"
        )
        (self.root / "policies").mkdir()
        (self.root / "policies" / "data-protection.txt").write_text(
            "Council policy on personal data — Aspire Trust contracts list:\n"
            "Refer to Item 4 of the 12 March cabinet minutes.\n"
        )
        (self.root / "binary.bin").write_bytes(b"\x00\x01\x02NOT-INDEXED")
        self.audit_path = self.root / "audit.log"
        self.audit = AuditLog(self.audit_path)
        self.corpus = Corpus(self.root, self.audit, ref="FOI-TEST-001")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # ---- list -------------------------------------------------------------
    def test_list_filters_to_allowed_extensions(self) -> None:
        files = self.corpus.list()
        self.assertIn("minutes/2026-03-cabinet.md", files)
        self.assertIn("policies/data-protection.txt", files)
        self.assertNotIn("binary.bin", files)

    def test_list_records_audit_entry(self) -> None:
        self.corpus.list()
        lines = self.audit_path.read_text().strip().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertIn('"event":"corpus.list"', lines[0])
        self.assertIn('"ref":"FOI-TEST-001"', lines[0])

    # ---- grep -------------------------------------------------------------
    def test_grep_matches_across_files(self) -> None:
        hits = self.corpus.grep(r"Aspire Trust")
        self.assertEqual(len(hits), 2)
        paths = {h.path for h in hits}
        self.assertEqual(paths, {"minutes/2026-03-cabinet.md", "policies/data-protection.txt"})

    def test_grep_audits_pattern_and_count(self) -> None:
        self.corpus.grep(r"SEND budget")
        last_line = self.audit_path.read_text().strip().splitlines()[-1]
        self.assertIn('"event":"corpus.grep"', last_line)
        self.assertIn('"pattern":"SEND budget"', last_line)
        self.assertIn('"hits":1', last_line)

    def test_grep_invalid_regex_raises(self) -> None:
        with self.assertRaises(CorpusError):
            self.corpus.grep("(unclosed")

    # ---- read -------------------------------------------------------------
    def test_read_full_file(self) -> None:
        body = self.corpus.read("minutes/2026-03-cabinet.md")
        self.assertIn("Cabinet 12 March 2026", body)
        self.assertIn("SEND budget", body)

    def test_read_line_range(self) -> None:
        body = self.corpus.read("minutes/2026-03-cabinet.md", lo=2, hi=2)
        self.assertEqual(body.strip(), "Item 4: SEND budget reallocation £2.4m to Aspire Trust")

    def test_read_disallowed_extension_raises(self) -> None:
        with self.assertRaises(CorpusError):
            self.corpus.read("binary.bin")

    # ---- snippet ----------------------------------------------------------
    def test_snippet_returns_window(self) -> None:
        body = self.corpus.snippet("minutes/2026-03-cabinet.md", line_no=2, n=1)
        self.assertIn("Cabinet 12 March 2026", body)
        self.assertIn("SEND budget", body)
        self.assertIn("Item 5: agreed.", body)

    # ---- safety -----------------------------------------------------------
    def test_path_traversal_blocked(self) -> None:
        with self.assertRaises(CorpusError):
            self.corpus.read("../../../../etc/passwd")
        with self.assertRaises(CorpusError):
            self.corpus.list("../..")

    def test_audit_chain_intact_after_mixed_calls(self) -> None:
        self.corpus.list()
        self.corpus.grep("Aspire")
        self.corpus.read("policies/data-protection.txt")
        # All events recorded with stable ref + chained hashes
        lines = self.audit_path.read_text().strip().splitlines()
        self.assertEqual(len(lines), 3)
        events = []
        prev_hash = "0" * 64
        import json
        for ln in lines:
            entry = json.loads(ln)
            self.assertEqual(entry["prev_hash"], prev_hash)
            self.assertEqual(entry["ref"], "FOI-TEST-001")
            events.append(entry["event"])
            prev_hash = entry["hash"]
        self.assertEqual(events, ["corpus.list", "corpus.grep", "corpus.read"])


if __name__ == "__main__":
    unittest.main()
