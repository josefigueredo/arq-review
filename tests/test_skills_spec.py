from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

import helpers
import skillspec

GOOD = "Use when something. Another sentence."


def make_skill(folder: str, frontmatter: "str | None", published_name: "str | None" = None) -> "list[str]":
    """Errors reported for a skill whose SKILL.md has exactly this frontmatter (None = no frontmatter at all)."""
    with tempfile.TemporaryDirectory() as tmp:
        skill = Path(tmp) / folder
        skill.mkdir()
        text = "# no frontmatter\n" if frontmatter is None else f"---\n{frontmatter}\n---\n\n# body\n"
        (skill / "SKILL.md").write_text(text, encoding="utf-8")
        return skillspec.check_skill(skill, published_name)


class ReferenceTest(unittest.TestCase):
    """The reference port must bite: each broken fixture fails with the rule it breaks."""

    def assertRejects(self, folder, frontmatter, fragment):
        errors = make_skill(folder, frontmatter)
        self.assertTrue(any(fragment in e for e in errors), errors)

    def test_valid_with_folded_block_and_metadata(self):
        fm = f"name: ok-skill\ndescription: >\n  {GOOD}\n  More text.\nmetadata:\n  author: x\ncompatibility: Needs python3."
        self.assertEqual(make_skill("ok-skill", fm), [])

    def test_field_outside_the_spec(self):
        self.assertRejects("ok", f"name: ok\ndescription: {GOOD}\nversion: 1", "unexpected frontmatter fields: version")

    def test_uppercase_name(self):
        self.assertRejects("Ok", f"name: Ok\ndescription: {GOOD}", "must be lowercase")

    def test_consecutive_hyphens(self):
        self.assertRejects("a--b", f"name: a--b\ndescription: {GOOD}", "consecutive hyphens")

    def test_hyphen_at_the_edge(self):
        self.assertRejects("-ab", f"name: -ab\ndescription: {GOOD}", "starts or ends with a hyphen")

    def test_name_differs_from_folder(self):
        self.assertRejects("folder", f"name: other\ndescription: {GOOD}", "does not match 'folder'")

    def test_missing_description(self):
        self.assertRejects("ok", "name: ok", "missing required field: description")

    def test_description_too_long(self):
        self.assertRejects("ok", f"name: ok\ndescription: {'x' * 1025}", "description is 1025 chars")

    def test_compatibility_too_long(self):
        self.assertRejects("ok", f"name: ok\ndescription: {GOOD}\ncompatibility: {'x' * 501}", "compatibility is 501 chars")

    def test_no_frontmatter(self):
        self.assertRejects("ok", None, "no YAML frontmatter")

    def test_name_too_long(self):
        name = "a" * 65
        self.assertRejects(name, f"name: {name}\ndescription: {GOOD}", "is 65 chars, max 64")

    def test_published_name_replaces_the_folder_rule(self):
        self.assertEqual(make_skill("clone-dir", f"name: real\ndescription: {GOOD}", published_name="real"), [])


class RepoSkillsTest(unittest.TestCase):
    def test_every_skill_conforms(self):
        skills = skillspec.discover(helpers.ROOT)
        self.assertTrue(skills)
        for skill in skills:
            self.assertEqual(skillspec.check_skill(skill), [], skill.name)

    def test_discovered_skills_are_the_ones_install_sh_links(self):
        script = (helpers.ROOT / "install.sh").read_text(encoding="utf-8")
        linked = re.search(r"^for skill in ([\w -]+); do$", script, re.M)
        self.assertIsNotNone(linked, "install.sh no longer has a `for skill in ...; do` loop")
        self.assertEqual(sorted(p.name for p in skillspec.discover(helpers.ROOT)), sorted(linked.group(1).split()))


if __name__ == "__main__":
    unittest.main()
