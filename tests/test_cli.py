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
