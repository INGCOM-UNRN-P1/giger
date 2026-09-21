"""Tests de integración de la CLI de GIGER."""

import json
from pathlib import Path
from typer.testing import CliRunner
from giger.cli import app

runner = CliRunner()


def test_cli_version():
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert "GIGER" in res.stdout


def test_cli_callgraph_json(tmp_path):
    fuente = tmp_path / "code.c"
    fuente.write_text("int f() { return 1; }\nint main() { f(); return 0; }\n")

    res = runner.invoke(app, ["callgraph", str(fuente), "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["total_funciones"] == 2
    assert "main" in data["funciones"]


def test_cli_callgraph_mermaid(tmp_path):
    fuente = tmp_path / "code.c"
    fuente.write_text("int f() { return 1; }\nint main() { f(); return 0; }\n")

    res = runner.invoke(app, ["callgraph", str(fuente), "--mermaid"])
    assert res.exit_code == 0
    assert "graph TD" in res.stdout


def test_cli_callgraph_mermaid_con_huerfanas(tmp_path):
    fuente = tmp_path / "dead.c"
    fuente.write_text("void huerfana() {}\nint main() { return 0; }\n")

    res = runner.invoke(app, ["callgraph", str(fuente), "--mermaid"])
    assert res.exit_code == 0
    assert "graph TD" in res.stdout
    assert "huerfana" in res.stdout
    assert "No invocada" in res.stdout


def test_cli_doctor():
    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 0
    assert "doctor" in res.stdout.lower()

    res_json = runner.invoke(app, ["doctor", "--json"])
    assert res_json.exit_code == 0
    data = json.loads(res_json.stdout)
    assert data["herramienta"] == "giger"
    assert data["ok"] is True


def test_huerfanas_semantica_de_salida_y_texto_del_reporte(tmp_path):
    """GIGER-D0303 / D0402: el reporte no miente sobre main() y hay salida 1 opt-in."""
    f = tmp_path / "m.c"
    f.write_text("void muerta(void) {}\nint main(void) { return 0; }\n")
    assert runner.invoke(app, ["check", str(f)]).exit_code == 0
    assert runner.invoke(app, ["check", str(f), "--fail-on-orphans"]).exit_code == 1
    assert runner.invoke(app, ["check", str(f), "--json", "--fail-on-orphans"]).exit_code == 1
    md = tmp_path / "r.md"
    res = runner.invoke(app, ["report", str(f), "-o", str(md)])
    texto = md.read_text(encoding="utf-8")
    assert "desde `main()`" not in texto
    assert "ninguna otra función de este archivo" in texto
    limpio = tmp_path / "ok.c"
    limpio.write_text("int main(void) { return 0; }\n")
    assert runner.invoke(app, ["check", str(limpio), "--fail-on-orphans"]).exit_code == 0
