"""arq: CLI of arq-review. Domain errors print `error: ...` and exit 1; argparse usage errors exit 2."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path
from typing import Callable, List, Mapping, Optional

from arqlib import config as cfg
from arqlib import fields, review, state, triage
from arqlib.board import render_board
from arqlib.apply import apply_followups, apply_plan, ensure_request, known_from_journal, sync_epic, sync_progress
from arqlib.progress import active_nodes, done_nodes
from arqlib.constraints import lint
from arqlib.evaluate import evaluate_files
from arqlib.jira import Jira, JiraError, check_key
from arqlib.journal import journal, read_entries
from arqlib.paths import CONTRACT
from arqlib.summary import unwrap
from arqlib.preview import render_html
from arqlib.render import assert_rendered, load_template, matches_template
from arqlib.structure import base_labels, build_plan, followup_plan, pry_label
from arqlib.timebox import add_business_days, is_overdue

APPLY_HINT = ("dry run: no se escribió nada. Para ejecutarlo, el usuario corre el mismo comando con --apply "
              "(en Claude Code, con !).")
PUBLIC_TEMPLATES = {"jsm-pedido-info.md": "esperando-info", "jsm-devolucion.md": "publicado",
                    "jsm-cierre.md": "propuesta-rechazo"}


class Context:
    def __init__(self, repo: Path, env: Mapping[str, str], client_factory: Optional[Callable[[], object]],
                 today: date):
        self.repo, self.env, self.client_factory, self.today = repo, env, client_factory, today

    def client(self, command: str):
        if self.client_factory is not None:
            return self.client_factory()
        base, email, token = cfg.credentials(self.env)
        return Jira(base, email, token, journal=journal(self.repo, command))


def _init(ctx: Context, args) -> int:
    created = cfg.init_repo(ctx.repo)
    print("\n".join(f"creado {p}" for p in created) or "el repo ya estaba inicializado")
    return 0


def _path(ctx: Context, args) -> int:
    print(CONTRACT)
    return 0


def _new(ctx: Context, args) -> int:
    review.check_pry(args.pry)
    review.check_email(args.contacto)
    pedido = sys.stdin.read() if args.pedido == "-" else Path(args.pedido).read_text(encoding="utf-8")
    path = review.new_review(ctx.repo, args.pry, args.nombre, pedido, args.contacto, args.head or "")
    print(f"creado {path.relative_to(ctx.repo)} (estado: recibido)")
    return 0


def _show(ctx: Context, args) -> int:
    meta, _ = review.load(ctx.repo, args.pry)
    for key, value in meta.items():
        print(f"{key}: {value}")
    return 0


def _triage(ctx: Context, args) -> int:
    meta, body = review.load(ctx.repo, args.pry)
    if meta.get("epica"):
        raise ValueError(f"{args.pry} ya tiene épica ({meta['epica']}): el nivel no se puede cambiar")
    nivel = triage.classify(triage.parse_answers(args.answers))
    meta = state.transition(meta, "triado")
    meta["nivel"] = nivel
    review.save(ctx.repo, args.pry, meta, body)
    print(f"nivel: {nivel}")
    return 0


def _set(ctx: Context, args) -> int:
    meta, body = review.load(ctx.repo, args.pry)
    updates = fields.parse_updates(args.updates)
    review.save(ctx.repo, args.pry, fields.apply_updates(meta, updates), body)
    print("actualizado: " + ", ".join(updates))
    return 0


def _state(ctx: Context, args) -> int:
    meta, body = review.load(ctx.repo, args.pry)
    meta = state.transition(meta, args.to, args.resultado or "")
    review.save(ctx.repo, args.pry, meta, body)
    print(f"estado: {meta['estado']}")
    return 0


def _timebox(ctx: Context, args) -> int:
    today = date.fromisoformat(args.today) if args.today else ctx.today
    meta, body = review.load(ctx.repo, args.pry)
    if not meta.get("vence"):
        meta["vence"] = add_business_days(today, cfg.load_config(ctx.repo)["timebox_dias_habiles"]).isoformat()
        review.save(ctx.repo, args.pry, meta, body)
    overdue = is_overdue(meta["vence"], today)
    print(f"vence: {meta['vence']} ({'vencido' if overdue else 'en plazo'})")
    if overdue and meta.get("estado") == "esperando-info":
        print(f"siguiente paso: arq state {args.pry} --to propuesta-rechazo")
    return 0


def _lint(ctx: Context, args) -> int:
    path = Path(args.file) if args.file else CONTRACT / "constraints.md"
    errors = lint(path.read_text(encoding="utf-8"))
    for error in errors:
        print(error)
    if errors:
        return 1
    print(f"ok: {path}")
    return 0


def _print_plan(plan: dict) -> None:
    print(f"épica     {plan['epic']['summary']}  [{' '.join(plan['epic']['labels'])}]")
    for item in plan["items"]:
        print(f"  {item['type']:<8}{item['summary']}")
        for sub in item["subtasks"]:
            print(f"    sub-task {sub['summary']}  [{sub['labels'][-1]}]")


def _jira(ctx: Context, args) -> int:
    meta, body = review.load(ctx.repo, args.pry)
    config = cfg.load_config(ctx.repo, require_canal=args.apply)
    plan = build_plan(meta, validacion=args.con_validacion, review_body=body)
    _print_plan(plan)
    if args.html:
        Path(args.html).write_text(render_html(plan, meta), encoding="utf-8")
        print(f"vista previa: {args.html}")
    if not args.apply:
        print(APPLY_HINT)
        return 0
    client = ctx.client("jira")
    labels = base_labels(meta)
    known, known_jsm = known_from_journal(read_entries(ctx.repo), labels[0], meta["pry"])
    result = apply_plan(plan, client, config["jira_project"], config["issue_types"], known=known)
    meta["epica"] = result["epica"]
    review.save(ctx.repo, args.pry, meta, body)

    def on_created(key: str) -> None:
        meta["jsm"] = key
        review.save(ctx.repo, args.pry, meta, body)

    def on_ready() -> None:
        meta["jsm_listo"] = "si"
        review.save(ctx.repo, args.pry, meta, body)

    description = (f"Pedido {meta['pry']} ({meta.get('nombre', '')}). En este ticket conversamos con Arquitectura "
                   "hasta cerrar la revisión.")
    try:
        jsm, created = ensure_request(meta, client, config, description, labels, on_created, on_ready,
                                      known_jsm=known_jsm)
    except JiraError as exc:
        if meta.get("jsm"):
            raise JiraError(f"{exc}. El pedido {meta['jsm']} quedó creado: volver a correr "
                            f"`arq jira {args.pry} --apply` para completar labels, participantes y link") from exc
        raise
    if created:  # the epic was written before the ticket existed: bring its summary up to date now
        sync_epic(client, result["epica"], build_plan(meta, validacion=args.con_validacion, review_body=body)["epic"])
    published = any(e.get("action") in ("jsm-comment", "comment") and e.get("key") == meta.get("jsm") and e.get("public")
                    for e in read_entries(ctx.repo))
    done = done_nodes(meta, plan, info_published=published)
    progress = sync_progress(client, labels[0], result["nodes"], done, active=active_nodes(meta, plan, done))
    print(f"épica: {result['epica']} (creados {len(result['created'])}, existentes {len(result['reused'])}; "
          f"descripciones actualizadas: {len(result['updated'])}; tareas movidas a Done: {len(progress['moved'])}, "
          f"a En curso: {len(progress['started'])})")
    if progress["blocked"]:
        print("sin transición a Done en su workflow (moverlas a mano): " + ", ".join(progress["blocked"]))
    if progress["blocked_start"]:
        print("sin transición a En curso en su workflow (moverlas a mano): " + ", ".join(progress["blocked_start"]))
    print(f"jsm: {jsm} ({'creado' if created else 'ya existía'}; labels, participantes y link al día)")
    return 0


def _jsm(ctx: Context, args) -> int:
    meta, _ = review.load(ctx.repo, args.pry)
    software = cfg.load_config(ctx.repo).get("canal_requirente", "jsm") == "software"
    if args.internal and software:
        raise ValueError("el help desk no tiene notas internas (todo comentario lo ve el requirente): "
                         "el debate técnico va en la épica ARQ")
    text = Path(args.file).read_text(encoding="utf-8").strip()
    assert_rendered(text)
    if args.public:
        if args.template not in PUBLIC_TEMPLATES:
            raise ValueError(f"una respuesta pública necesita --template ({', '.join(PUBLIC_TEMPLATES)})")
        if not matches_template(load_template(args.template), text):
            raise ValueError(f"el texto no sigue la plantilla {args.template}: redactarlo desde ella")
        if meta["pry"] not in text:
            raise ValueError(f"el texto no menciona {meta['pry']}: ¿es la respuesta de otro pedido?")
        needed = PUBLIC_TEMPLATES[args.template]
        if meta.get("estado") != needed:
            raise ValueError(f"{args.template} se publica en estado {needed}; el pedido está en {meta.get('estado')}")
    if not meta.get("jsm"):
        raise ValueError(f"{args.pry} no tiene pedido JSM: correr `arq jira {args.pry} --apply` primero")
    check_key(meta["jsm"])
    # Jira shows every newline inside a paragraph as a visible break: send whole paragraphs and bullets.
    text = unwrap(text)
    kind = "respuesta pública al requirente" if args.public else "nota interna"
    print(f"{kind} en {meta['jsm']}:\n\n{text}\n")
    if not args.apply:
        print(APPLY_HINT)
        return 0
    for entry in read_entries(ctx.repo):
        sent = (entry.get("key"), entry.get("public"), unwrap(entry.get("body") or ""))
        if entry.get("action") in ("jsm-comment", "comment") and sent == (meta["jsm"], args.public, text):
            raise ValueError(f"ya se publicó este mismo mensaje en {meta['jsm']} ({entry.get('ts', 'sin fecha')}): "
                             "no se reenvía")
    client = ctx.client("jsm")
    if software:
        client.add_comment(meta["jsm"], text)
    else:
        client.comment(meta["jsm"], text, public=args.public)
    print(f"publicado: {kind} en {meta['jsm']}")
    return 0


def _seguimiento(ctx: Context, args) -> int:
    meta, _ = review.load(ctx.repo, args.pry)
    if meta.get("veredicto") != "aprobar-con-condiciones" or meta.get("estado") not in ("publicado", "cerrado"):
        raise ValueError("las sub-tasks de seguimiento son para un veredicto aprobar-con-condiciones ya publicado")
    follow = followup_plan(meta, args.condiciones)
    print(f"bajo {follow['parent_summary']}:")
    for sub in follow["subtasks"]:
        print(f"  sub-task {sub['summary']}")
    if not args.apply:
        print(APPLY_HINT)
        return 0
    config = cfg.load_config(ctx.repo)
    label = base_labels(meta)[0]
    known, _ = known_from_journal(read_entries(ctx.repo), label, meta["pry"])
    result = apply_followups(follow, label, ctx.client("seguimiento"), config["jira_project"], config["issue_types"],
                             known=known)
    print(f"seguimiento: creadas {len(result['created'])}, existentes {len(result['reused'])}")
    return 0


def _ver(ctx: Context, args) -> int:
    meta, _ = review.load(ctx.repo, args.pry)
    if not meta.get("epica"):
        raise ValueError(f"{args.pry} todavía no tiene épica: correr `arq jira {args.pry} --apply` primero")
    client = ctx.client("ver")
    links = not args.sin_links and sys.stdout.isatty()
    print(render_board(meta, client.search_board(pry_label(meta["pry"])), client.browse_url, links=links))
    return 0


def _link(ctx: Context, args) -> int:
    check_key(args.inward)
    check_key(args.outward)
    link_type = cfg.load_config(ctx.repo)["link_type"]
    print(f"link {link_type}: {args.inward} → {args.outward}")
    if not args.apply:
        print(APPLY_HINT)
        return 0
    ctx.client("link").link(args.inward, args.outward, link_type)
    print("linkeado")
    return 0


def _eval(ctx: Context, args) -> int:
    failures = evaluate_files(Path(args.golden), Path(args.review))
    for failure in failures:
        print(f"✗ {failure}")
    if failures:
        return 1
    print("ok: cumple la rúbrica")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="arq", description="Revisión de Arquitectura de pedidos PRY.")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, handler: Callable, help_text: str) -> argparse.ArgumentParser:
        command = sub.add_parser(name, help=help_text)
        command.set_defaults(handler=handler)
        return command

    add("init", _init, "inicializa el repo de reviews (.arq/config.json y reviews/)")
    add("path", _path, "imprime la carpeta del contrato")
    p = add("new", _new, "registra un pedido nuevo")
    p.add_argument("pry")
    p.add_argument("--nombre", required=True)
    p.add_argument("--pedido", required=True, help="archivo con el texto del pedido, o - para leer de stdin")
    p.add_argument("--contacto", required=True, help="email del contacto principal (requirente)")
    p.add_argument("--head", help="email del head o stakeholder (participante del pedido JSM)")
    p = add("show", _show, "muestra el estado de un pedido")
    p.add_argument("pry")
    p = add("triage", _triage, "clasifica el pedido en simple o complejo (se puede repetir hasta crear la épica)")
    p.add_argument("pry")
    p.add_argument("--answers", required=True, help="id=si|no separados por coma (ver contract/triage.md)")
    p = add("set", _set, "actualiza campos del architect o el firmante")
    p.add_argument("pry")
    p.add_argument("updates", nargs="+", metavar="campo=valor")
    p = add("state", _state, "cambia el estado del pedido")
    p.add_argument("pry")
    p.add_argument("--to", required=True)
    p.add_argument("--resultado")
    p = add("timebox", _timebox, "arranca o consulta el plazo")
    p.add_argument("pry")
    p.add_argument("--today", help="AAAA-MM-DD (por defecto, hoy)")
    p = add("lint", _lint, "valida constraints.md")
    p.add_argument("--file")
    p = add("jira", _jira, "crea épica, tareas y pedido JSM (dry run salvo --apply)")
    p.add_argument("pry")
    p.add_argument("--html")
    p.add_argument("--con-validacion", action="store_true", help="incluye la historia opcional de validación técnica")
    p.add_argument("--apply", action="store_true")
    p = add("jsm", _jsm, "comenta en el pedido JSM (dry run salvo --apply)")
    p.add_argument("pry")
    p.add_argument("--file", required=True)
    p.add_argument("--template", help="plantilla del mensaje público (" + ", ".join(PUBLIC_TEMPLATES) + ")")
    channel = p.add_mutually_exclusive_group(required=True)
    channel.add_argument("--public", action="store_true", help="respuesta al requirente")
    channel.add_argument("--internal", action="store_true", help="nota interna")
    p.add_argument("--apply", action="store_true")
    p = add("seguimiento", _seguimiento, "una sub-task por condición de un aprobar-con-condiciones (dry run salvo --apply)")
    p.add_argument("pry")
    p.add_argument("condiciones", nargs="+")
    p.add_argument("--apply", action="store_true")
    p = add("ver", _ver, "muestra el ticket del requirente y el árbol de la épica con su estado (solo lectura)")
    p.add_argument("pry")
    p.add_argument("--sin-links", action="store_true", help="sin links clickeables en la terminal")
    p = add("link", _link, "linkea dos issues (dry run salvo --apply)")
    p.add_argument("inward")
    p.add_argument("outward")
    p.add_argument("--apply", action="store_true")
    p = add("eval", _eval, "evalúa un review contra un golden case")
    p.add_argument("golden")
    p.add_argument("review")
    return parser


def main(argv: Optional[List[str]] = None, env: Optional[Mapping[str, str]] = None, cwd: Optional[str] = None,
         client_factory: Optional[Callable[[], object]] = None, today: Optional[date] = None) -> int:
    args = build_parser().parse_args(argv)
    ctx = Context(Path(cwd or os.getcwd()).resolve(), os.environ if env is None else env, client_factory,
                  today or date.today())
    try:
        return args.handler(ctx, args)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
