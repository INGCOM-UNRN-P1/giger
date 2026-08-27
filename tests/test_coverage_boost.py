"""Tests adicionales para maximizar la cobertura en GIGER."""

import json
from pathlib import Path
from typer.testing import CliRunner
import giger.cli
from giger.cli import app
from giger.core.graph import analizar_callgraph_archivo
from giger.ripley_plugin import GigerPlugin

runner = CliRunner()


def test_plugin_execution(tmp_path):
    p = GigerPlugin()
    assert p.is_available() is True

    f = tmp_path / "grafo.c"
    f.write_text("void muerto() {} int main() { return 0; }\n")
    res = p.execute(tmp_path, {})
    assert res["ok"] is True
    assert len(res["observaciones"]) == 1


def test_cli_callgraph_rich_output(tmp_path):
    f = tmp_path / "code.c"
    f.write_text("""
    int rec(int n) { if (n <= 0) return 0; return rec(n - 1); }
    void huerfana(void) {}
    int main(void) { rec(5); return 0; }
    """)

    res = runner.invoke(app, ["callgraph", str(f)])
    assert res.exit_code == 0
    assert "Mapa de Llamadas" in res.stdout
    assert "Funciones recursivas" in res.stdout
    assert "Funciones no invocadas" in res.stdout


def test_cli_file_not_found():
    res = runner.invoke(app, ["callgraph", "/no/existe.c"])
    assert res.exit_code == 2


def test_callgraph_nonexistent_file(tmp_path):
    cg = analizar_callgraph_archivo(tmp_path / "no_existe.c")
    assert len(cg.funciones) == 0


def test_cli_main_block(monkeypatch):
    monkeypatch.setattr("sys.argv", ["giger", "--version"])
    try:
        giger.cli.main()
    except SystemExit as e:
        assert e.code == 0
