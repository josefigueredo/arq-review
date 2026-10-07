from __future__ import annotations

import json
import unittest

import helpers
from arqlib.journal import journal, read_entries


class JournalTest(unittest.TestCase):
    def test_appends_json_lines(self):
        repo = helpers.make_repo()
        write = journal(repo, "jira", now=lambda: "2026-10-07T21:00:00Z")
        write({"action": "create", "key": "ARQ-1"})
        write({"action": "link", "inward": "JSM-1", "outward": "ARQ-1"})
        lines = (repo / ".arq" / "jira-writes.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(json.loads(lines[0]), {"ts": "2026-10-07T21:00:00Z", "tool": "arq-review", "command": "jira",
                                                "action": "create", "key": "ARQ-1"})
        self.assertEqual(len(lines), 2)

    def test_never_raises(self):
        repo = helpers.make_repo()
        (repo / ".arq").write_text("soy un archivo, no una carpeta", encoding="utf-8")
        journal(repo, "jira")({"action": "create"})  # no exception

    def test_read_entries_skips_broken_lines(self):
        repo = helpers.make_repo()
        write = journal(repo, "jira", now=lambda: "t")
        write({"action": "create", "key": "ARQ-1"})
        with (repo / ".arq" / "jira-writes.jsonl").open("a", encoding="utf-8") as handle:
            handle.write("{roto\n")
        self.assertEqual([e["key"] for e in read_entries(repo)], ["ARQ-1"])
        self.assertEqual(read_entries(helpers.make_repo()), [])


if __name__ == "__main__":
    unittest.main()
