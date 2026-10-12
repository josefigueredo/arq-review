"""The docs are what a new install reads: every link lands, the index covers each piece, and only the generic Jira variables are named."""
from __future__ import annotations

import re
import unittest

from pathlib import Path

from helpers import ROOT
from arqlib import config

DOCS = ROOT / "docs"
README = ROOT / "README.md"
SIMPLE = (DOCS / "instalacion.md").read_text(encoding="utf-8")
DETAILED = (DOCS / "instalacion-detallada.md").read_text(encoding="utf-8")
PAGES = [README, DOCS / "instalacion.md", DOCS / "instalacion-detallada.md", DOCS / "showcase.md", DOCS / "referencia.md"]


def slug(heading: str) -> str:
    """GitHub's anchor for a heading: lowercase, punctuation dropped, spaces to hyphens."""
    text = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return text.replace(" ", "-")


def anchors(path: Path) -> set:
    return {slug(m.group(2)) for m in re.finditer(r"^(#{1,6}) (.+)$", path.read_text(encoding="utf-8"), re.M)}


class ReadmeTest(unittest.TestCase):
    def test_every_relative_link_and_image_in_the_docs_lands_on_a_file_and_an_anchor(self):
        link = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)\)")
        for page in PAGES:
            for target in link.findall(page.read_text(encoding="utf-8")):
                if re.match(r"[a-z]+:", target):  # https:, mailto:
                    continue
                path, _, fragment = target.partition("#")
                dest = (page.parent / path).resolve() if path else page
                self.assertTrue(dest.exists(), f"{page.name} links to {target}, which does not exist")
                if fragment and dest.suffix == ".md":
                    self.assertIn(fragment, anchors(dest), f"{page.name} links to {target}: no such heading")

    def test_the_index_links_each_piece_to_the_showcase_and_the_install_guide(self):
        rows = [line for line in README.read_text(encoding="utf-8").splitlines() if re.match(r"\| \*\*`(arq-manager|arq-architect|arq)`", line)]
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertIn("docs/showcase.md#", row)
            self.assertIn("docs/instalacion.md#", row)

    def test_the_readme_covers_both_skills_and_the_cli(self):
        text = README.read_text(encoding="utf-8")
        for name in ("arq-manager", "arq-architect", "`arq`"):
            self.assertIn(name, text)

    def test_the_guides_name_the_generic_credentials_and_warn_about_token_scopes(self):
        for text in (SIMPLE, DETAILED):
            for name in config._ENV:
                self.assertIn(name, text)
            self.assertIn("sin alcance", text.lower())
            self.assertIn("api.atlassian.com", text)
            self.assertNotIn("IC_JIRA", text)

    def test_the_cursor_guide_has_no_scripts_to_run(self):
        # it is for someone who talks to the agent: the only code block is the three variables of the credentials step
        blocks = SIMPLE.split("```")[1::2]
        self.assertEqual(len(blocks), 1)
        self.assertIn("JIRA_API_TOKEN", blocks[0])

    def test_the_reference_keeps_the_original_readme_sections(self):
        text = (DOCS / "referencia.md").read_text(encoding="utf-8")
        for title in ("## Instalar", "## Repo de reviews del equipo", "## Comandos", "## Garantías", "## Tests"):
            self.assertIn(title, text)


if __name__ == "__main__":
    unittest.main()
