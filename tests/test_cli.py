from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date

import helpers
from arqlib.cli import main
from arqlib.journal import journal
from arqlib.render import load_template, render
from arqlib.review import load

ALL_NO = ("multi_cuenta=no,migracion=no,fecha_comprometida=no,otros_equipos=no,"
          "datos_sensibles_o_ia=no,larga_o_productiva=no")
PRY = "PRY-2026-0028"
CONTACTO = "requester@example.com"


def run(repo, *argv, fake=None, env=None, today=date(2026, 10, 7)):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(list(argv), env=env if env is not None else {}, cwd=str(repo),
                    client_factory=(lambda: fake) if fake is not None else None, today=today)
    return code, out.getvalue(), err.getvalue()


def ready_repo():
    repo = helpers.make_repo()
    run(repo, "init")
    path = repo / ".arq" / "config.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(jsm_project="JSM", jsm_service_desk_id="3", jsm_request_type_id="41")
    path.write_text(json.dumps(data), encoding="utf-8")
    (repo / "pedido.txt").write_text("Habilitar una G6e.xlarge", encoding="utf-8")
    run(repo, "new", PRY, "--nombre", "PoC modelos IA Locales", "--pedido", str(repo / "pedido.txt"),
        "--contacto", CONTACTO, "--head", "reviewer@example.com")
    return repo


def opened_repo(fake):
    repo = ready_repo()
    run(repo, "triage", PRY, "--answers", ALL_NO)
    run(repo, "jira", PRY, "--apply", fake=fake)
    return repo


def write(repo, name, text):
    (repo / name).write_text(text, encoding="utf-8")
    return str(repo / name)


def pedido_info():
    return render(load_template("jsm-pedido-info.md"), {
        "contacto": "Juan Pablo", "pry": PRY, "nombre": "PoC", "faltantes": "- Fecha de baja",
        "motivo": "Sin fecha de baja no se puede estimar el costo.", "vence": "2026-10-21"})


class CliTest(unittest.TestCase):
    def test_simple_flow(self):
        repo, fake = ready_repo(), helpers.FakeJira()
        self.assertEqual(run(repo, "triage", PRY, "--answers", ALL_NO)[:2], (0, "nivel: simple\n"))

        code, out, _ = run(repo, "jira", PRY, "--html", str(repo / "vista.html"), fake=fake)
        self.assertEqual(code, 0)
        self.assertIn("dry run", out)
        self.assertTrue((repo / "vista.html").exists())
        self.assertEqual(fake.issues, {})

        code, out, _ = run(repo, "jira", PRY, "--apply", fake=fake)
        self.assertEqual(code, 0)
        meta, _ = load(repo, PRY)
        self.assertEqual((meta["epica"], meta["jsm"], meta["jsm_listo"]), ("ARQ-1", "JSM-1", "si"))
        self.assertEqual(fake.issues["JSM-1"]["reporter"], "acc-pablo")
        self.assertEqual(fake.links, [("JSM-1", "ARQ-1", "Relates")])

        self.assertIn("vence: 2026-10-21 (en plazo)", run(repo, "timebox", PRY)[1])
        self.assertEqual(run(repo, "state", PRY, "--to", "esperando-info")[0], 0)
        self.assertEqual(run(repo, "state", PRY, "--to", "esperando-info")[0], 0)  # repetir no rompe
        self.assertEqual(run(repo, "set", PRY, "faltantes=costo_estimado", "senales=finops")[0], 0)

        code, _, err = run(repo, "set", PRY, "veredicto=aprobar")
        self.assertEqual(code, 1)
        self.assertIn("input faltante", err)

    def test_retriage_until_the_epic_exists(self):
        repo, fake = ready_repo(), helpers.FakeJira()
        run(repo, "triage", PRY, "--answers", ALL_NO)
        code, out, _ = run(repo, "triage", PRY, "--answers", ALL_NO.replace("migracion=no", "migracion=si"))
        self.assertEqual((code, out), (0, "nivel: complejo\n"))
        run(repo, "jira", PRY, "--apply", fake=fake)
        code, _, err = run(repo, "triage", PRY, "--answers", ALL_NO)
        self.assertEqual(code, 1)
        self.assertIn("épica", err)

    def test_public_reply_needs_matching_template_and_state(self):
        fake = helpers.FakeJira()
        repo = opened_repo(fake)
        run(repo, "state", PRY, "--to", "esperando-info")
        info = write(repo, "info.md", pedido_info())

        code, _, err = run(repo, "jsm", PRY, "--file", info, "--public", fake=fake)
        self.assertEqual(code, 1)
        self.assertIn("--template", err)

        bad = write(repo, "bad.md", "Hola {{contacto}}")
        code, _, err = run(repo, "jsm", PRY, "--file", bad, "--public", "--template", "jsm-pedido-info.md", fake=fake)
        self.assertEqual(code, 1)
        self.assertIn("placeholders", err)

        free = write(repo, "free.md", "127.0.0.1 localhost")
        code, _, err = run(repo, "jsm", PRY, "--file", free, "--public", "--template", "jsm-pedido-info.md", fake=fake)
        self.assertEqual(code, 1)
        self.assertIn("no sigue la plantilla", err)

        devolucion = write(repo, "dev.md", render(load_template("jsm-devolucion.md"), {
            "contacto": "Juan Pablo", "pry": PRY, "nombre": "PoC", "veredicto": "Aprobado con condiciones",
            "resumen": "r", "recomendaciones": "- r", "condiciones": "- c", "senales": "- s", "link": "https://x"}))
        code, _, err = run(repo, "jsm", PRY, "--file", devolucion, "--public", "--template", "jsm-devolucion.md",
                           fake=fake)
        self.assertEqual(code, 1)
        self.assertIn("se publica en estado publicado", err)  # una devolución nunca sale antes de la firma

        code, out, _ = run(repo, "jsm", PRY, "--file", info, "--public", "--template", "jsm-pedido-info.md", fake=fake)
        self.assertEqual((code, fake.comments), (0, []))
        self.assertIn("respuesta pública", out)
        run(repo, "jsm", PRY, "--file", info, "--public", "--template", "jsm-pedido-info.md", "--apply", fake=fake)
        run(repo, "jsm", PRY, "--file", free, "--internal", "--apply", fake=fake)
        self.assertEqual([c[2] for c in fake.comments], [True, False])

    def test_followups_only_for_published_conditional_approval(self):
        fake = helpers.FakeJira()
        repo = opened_repo(fake)
        code, _, err = run(repo, "seguimiento", PRY, "Apagado fuera de horario", fake=fake)
        self.assertEqual(code, 1)
        self.assertIn("aprobar-con-condiciones", err)

        run(repo, "state", PRY, "--to", "en-analisis")
        run(repo, "set", PRY, "veredicto=aprobar-con-condiciones")
        run(repo, "state", PRY, "--to", "en-firma")
        run(repo, "set", PRY, "firmante=edgardo.costilla")
        self.assertEqual(run(repo, "state", PRY, "--to", "publicado")[0], 0)

        code, out, _ = run(repo, "seguimiento", PRY, "Apagado fuera de horario", fake=fake)
        self.assertEqual(code, 0)
        self.assertIn("Condición: Apagado fuera de horario", out)
        before = len(fake.issues)
        run(repo, "seguimiento", PRY, "Apagado fuera de horario", "--apply", fake=fake)
        run(repo, "seguimiento", PRY, "Apagado fuera de horario", "--apply", fake=fake)
        self.assertEqual(len(fake.issues), before + 1)
        self.assertEqual(run(repo, "state", PRY, "--to", "cerrado", "--resultado", "aprobado")[0], 1)
        self.assertEqual(run(repo, "state", PRY, "--to", "cerrado", "--resultado", "condicionado")[0], 0)

    def test_signature_cannot_outlive_the_verdict_it_signed(self):
        fake = helpers.FakeJira()
        repo = opened_repo(fake)
        run(repo, "state", PRY, "--to", "en-analisis")
        self.assertEqual(run(repo, "set", PRY, "firmante=juan", "veredicto=aprobar")[0], 1)  # firma antes de en-firma
        run(repo, "set", PRY, "veredicto=aprobar")
        run(repo, "state", PRY, "--to", "en-firma")
        run(repo, "set", PRY, "firmante=juan")
        run(repo, "state", PRY, "--to", "en-analisis")
        run(repo, "set", PRY, "veredicto=rechazar")
        run(repo, "state", PRY, "--to", "en-firma")
        code, _, err = run(repo, "state", PRY, "--to", "publicado")
        self.assertEqual(code, 1)
        self.assertIn("firmante", err)  # la firma anterior no vale para el veredicto nuevo
        run(repo, "set", PRY, "firmante=juan")
        run(repo, "state", PRY, "--to", "publicado")
        self.assertEqual(run(repo, "set", PRY, "veredicto=aprobar")[0], 1)  # publicado: el veredicto queda fijo
        self.assertEqual(run(repo, "state", PRY, "--to", "cerrado", "--resultado", "aprobado")[0], 1)
        self.assertEqual(run(repo, "state", PRY, "--to", "cerrado", "--resultado", "rechazado")[0], 0)

    def test_same_public_reply_is_not_sent_twice(self):
        fake = helpers.FakeJira()
        repo = opened_repo(fake)
        run(repo, "state", PRY, "--to", "esperando-info")
        info = write(repo, "info.md", pedido_info())
        journal(repo, "jsm")({"action": "jsm-comment", "key": "JSM-1", "public": True, "body": pedido_info().strip()})
        code, _, err = run(repo, "jsm", PRY, "--file", info, "--public", "--template", "jsm-pedido-info.md", "--apply",
                           fake=fake)
        self.assertEqual((code, fake.comments), (1, []))
        self.assertIn("ya se publicó", err)

    def test_public_reply_must_name_this_request(self):
        fake = helpers.FakeJira()
        repo = opened_repo(fake)
        run(repo, "state", PRY, "--to", "esperando-info")
        other = write(repo, "other.md", pedido_info().replace(PRY, "PRY-2026-0026"))
        code, _, err = run(repo, "jsm", PRY, "--file", other, "--public", "--template", "jsm-pedido-info.md",
                           fake=fake)
        self.assertEqual(code, 1)
        self.assertIn(PRY, err)

    def test_bad_pry_never_touches_disk(self):
        repo = helpers.make_repo()
        run(repo, "init")
        code, _, err = run(repo, "new", "../../x", "--nombre", "x", "--pedido", "-", "--contacto", CONTACTO)
        self.assertEqual(code, 1)
        self.assertIn("PRY inválido", err)
        self.assertEqual(list((repo / "reviews").iterdir()), [])

    def test_missing_credentials(self):
        repo = ready_repo()
        run(repo, "triage", PRY, "--answers", ALL_NO)
        code, _, err = run(repo, "jira", PRY, "--apply")
        self.assertEqual(code, 1)
        self.assertIn("JIRA_API_TOKEN", err)

    def test_link_failure_is_completed_by_rerunning(self):
        repo, fake = ready_repo(), helpers.FakeJira()
        run(repo, "triage", PRY, "--answers", ALL_NO)
        fake.fail_link = True
        code, _, err = run(repo, "jira", PRY, "--apply", fake=fake)
        self.assertEqual(code, 1)
        self.assertIn("volver a correr", err)
        self.assertEqual((load(repo, PRY)[0]["jsm"], load(repo, PRY)[0]["jsm_listo"]), ("JSM-1", ""))
        fake.fail_link = False
        self.assertEqual(run(repo, "jira", PRY, "--apply", fake=fake)[0], 0)
        self.assertEqual(load(repo, PRY)[0]["jsm_listo"], "si")
        self.assertEqual(fake.requests, ["JSM-1"])

    def test_overdue_timebox_suggests_rejection_proposal(self):
        repo = ready_repo()
        run(repo, "triage", PRY, "--answers", ALL_NO)
        run(repo, "timebox", PRY)
        run(repo, "state", PRY, "--to", "esperando-info")
        code, out, _ = run(repo, "timebox", PRY, today=date(2026, 10, 22))
        self.assertIn("vencido", out)
        self.assertIn(f"arq state {PRY} --to propuesta-rechazo", out)

    def test_lint(self):
        repo = helpers.make_repo()
        self.assertEqual(run(repo, "lint")[0], 0)
        (repo / "c.md").write_text("### C-X-01 · t\n- **Severidad:** urgente\n", encoding="utf-8")
        code, out, _ = run(repo, "lint", "--file", str(repo / "c.md"))
        self.assertEqual(code, 1)
        self.assertIn("severidad inválida", out)

    def test_link_validates_keys(self):
        code, _, err = run(ready_repo(), "link", "JSM-1", "../x")
        self.assertEqual(code, 1)
        self.assertIn("clave de Jira inválida", err)

    def test_usage_error_exits_2(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            main(["inventado"])
        self.assertEqual(raised.exception.code, 2)

    def test_eval_reference(self):
        golden = helpers.ROOT / "tests" / "golden" / "PRY-2026-0028"
        code, out, _ = run(helpers.make_repo(), "eval", str(golden), str(golden / "reference.md"))
        self.assertEqual((code, out), (0, "ok: cumple la rúbrica\n"))


if __name__ == "__main__":
    unittest.main()
