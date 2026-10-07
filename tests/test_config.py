from __future__ import annotations

import json
import unittest

import helpers
from arqlib.config import ConfigError, credentials, init_repo, load_config


class ConfigTest(unittest.TestCase):
    def test_init_creates_config_and_reviews_and_is_idempotent(self):
        repo = helpers.make_repo()
        self.assertEqual(sorted(init_repo(repo)), [".arq/config.json", "reviews/"])
        self.assertEqual(init_repo(repo), [])
        self.assertEqual(load_config(repo)["timebox_dias_habiles"], 10)

    def test_missing_config_points_to_init(self):
        with self.assertRaisesRegex(ConfigError, "arq init"):
            load_config(helpers.make_repo())

    def test_invalid_json(self):
        repo = helpers.make_repo()
        (repo / ".arq").mkdir()
        (repo / ".arq" / "config.json").write_text("{nope", encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "JSON inválido"):
            load_config(repo)

    def test_require_jsm_needs_ids(self):
        repo = helpers.make_repo()
        init_repo(repo)
        with self.assertRaisesRegex(ConfigError, "jsm_service_desk_id"):
            load_config(repo, require_jsm=True)

    def _write(self, repo, **changes):
        path = repo / ".arq" / "config.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data.update(changes)
        path.write_text(json.dumps(data), encoding="utf-8")
        return data

    def test_missing_issue_type(self):
        repo = helpers.make_repo()
        init_repo(repo)
        types = dict(json.loads((repo / ".arq" / "config.json").read_text(encoding="utf-8"))["issue_types"])
        del types["subtask"]
        self._write(repo, issue_types=types)
        with self.assertRaisesRegex(ConfigError, "issue_types.subtask"):
            load_config(repo)

    def test_issue_types_must_be_an_object(self):
        repo = helpers.make_repo()
        init_repo(repo)
        self._write(repo, issue_types="Epic")
        with self.assertRaisesRegex(ConfigError, "issue_types"):
            load_config(repo)

    def test_require_jsm_needs_project_key(self):
        repo = helpers.make_repo()
        init_repo(repo)
        self._write(repo, jsm_service_desk_id="3", jsm_request_type_id="41")
        with self.assertRaisesRegex(ConfigError, "jsm_project"):
            load_config(repo, require_jsm=True)

    def test_credentials(self):
        env = {"JIRA_BASE_URL": "https://x.atlassian.net", "JIRA_EMAIL": "a@b", "JIRA_API_TOKEN": "t"}
        self.assertEqual(credentials(env), ("https://x.atlassian.net", "a@b", "t"))
        with self.assertRaisesRegex(ConfigError, "JIRA_API_TOKEN"):
            credentials({"JIRA_BASE_URL": "u", "JIRA_EMAIL": "e"})

    def test_credentials_require_https(self):
        with self.assertRaisesRegex(ConfigError, "https"):
            credentials({"JIRA_BASE_URL": "http://x.atlassian.net", "JIRA_EMAIL": "a@b", "JIRA_API_TOKEN": "t"})


if __name__ == "__main__":
    unittest.main()
