"""Team reviews repo settings (.arq/config.json) and Jira credentials from the environment."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Mapping, Tuple

DEFAULT_CONFIG = {
    "jira_project": "ARQ",
    "canal_requirente": "jsm",
    "jsm_project": "",
    "jsm_service_desk_id": "",
    "jsm_request_type_id": "",
    "issue_types": {"epic": "Epic", "story": "Story", "task": "Task", "subtask": "Subtask"},
    "link_type": "Relates",
    "timebox_dias_habiles": 10,
    "helpdesk_project": "",
    "helpdesk_issue_type": "",
}
CANALES = {"jsm": ("jsm_project", "jsm_service_desk_id", "jsm_request_type_id"),
           "software": ("helpdesk_project", "helpdesk_issue_type")}
_REQUIRED = ("jira_project", "issue_types", "link_type", "timebox_dias_habiles")
_ISSUE_TYPES = ("epic", "story", "task", "subtask")
_ENV = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")


class ConfigError(ValueError):
    pass


def config_path(repo: Path) -> Path:
    return repo / ".arq" / "config.json"


def init_repo(repo: Path) -> List[str]:
    created: List[str] = []
    path = config_path(repo)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        created.append(".arq/config.json")
    if not (repo / "reviews").exists():
        (repo / "reviews").mkdir(parents=True)
        created.append("reviews/")
    return created


def load_config(repo: Path, require_canal: bool = False) -> dict:
    path = config_path(repo)
    if not path.exists():
        raise ConfigError(f"falta {path}: correr `arq init` en el repo de reviews")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"JSON inválido en {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path} tiene que ser un objeto JSON")
    missing = [key for key in _REQUIRED if key not in data]
    types = data.get("issue_types")
    if "issue_types" in data and not isinstance(types, dict):
        raise ConfigError("issue_types tiene que ser un objeto: {\"epic\": ..., \"story\": ..., ...}")
    missing += [f"issue_types.{t}" for t in _ISSUE_TYPES if not (types or {}).get(t)]
    canal = data.get("canal_requirente", "jsm")
    if canal not in CANALES:
        raise ConfigError(f"canal_requirente inválido {canal!r}: usar {' o '.join(CANALES)}")
    if require_canal:
        missing += [key for key in CANALES[canal] if not str(data.get(key, "")).strip()]
    if missing:
        raise ConfigError(f"faltan en {path}: {', '.join(missing)}")
    if not isinstance(data["timebox_dias_habiles"], int) or data["timebox_dias_habiles"] < 1:
        raise ConfigError("timebox_dias_habiles tiene que ser un entero ≥ 1")
    return data


def credentials(env: Mapping[str, str]) -> Tuple[str, str, str]:
    missing = [name for name in _ENV if not env.get(name, "").strip()]
    if missing:
        raise ConfigError(f"faltan variables de entorno: {', '.join(missing)}")
    if not env["JIRA_BASE_URL"].startswith("https://"):
        raise ConfigError("JIRA_BASE_URL tiene que empezar con https:// (el token viaja en cada request)")
    return env["JIRA_BASE_URL"], env["JIRA_EMAIL"], env["JIRA_API_TOKEN"]
