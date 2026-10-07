from __future__ import annotations

import re
import unittest

import helpers
from arqlib.cli import build_parser

SKILLS = helpers.ROOT / "skills"


def subcommands():
    parser = build_parser()
    action = next(a for a in parser._actions if a.dest == "command")
    return set(action.choices)


class SkillsTest(unittest.TestCase):
    def test_both_skills_exist(self):
        found = sorted(p.parent.name for p in SKILLS.glob("*/SKILL.md"))
        self.assertEqual(found, ["arq-architect", "arq-manager"])

    def test_frontmatter(self):
        for name in ("arq-manager", "arq-architect"):
            text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(text.startswith(f"---\nname: {name}\ndescription: Use when "), name)

    def test_every_arq_command_mentioned_exists(self):
        known = subcommands()
        for path in SKILLS.glob("*/SKILL.md"):
            used = set(re.findall(r"`!? ?arq (\w+)", path.read_text(encoding="utf-8")))
            self.assertTrue(used, path)
            self.assertEqual(used - known, set(), path)

    def test_skills_never_run_apply_themselves(self):
        for path in SKILLS.glob("*/SKILL.md"):
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                if "--apply" in line and "arq " in line:
                    self.assertIn("!", line, f"{path.parent.name}: {line}")


if __name__ == "__main__":
    unittest.main()
