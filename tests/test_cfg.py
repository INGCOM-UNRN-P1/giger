"""Ola 19 (QoL #423): `giger cfg` arma el grafo de flujo de control de cada función y señala código
inalcanzable y bucles infinitos triviales."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from giger.cli import app
from giger.core.cfg import cfg_de_archivo, mermaid

runner = CliRunner()

FUENTE = """#include <stdio.h>
#include <stdlib.h>

int buscar(const int *v, int n, int x)
{
    for (int i = 0; i < n; i++)
    {
        if (v[i] == x)
        {
            return i;
            printf("encontrado\\n");
        }
    }
    return -1;
    puts("nunca");
}

int sumar_hasta(int n)
{
    int i = 0, s = 0;
    while (i < n)
    {
        s += i;
    }
    return s;
}

void menu(void)
{
    while (1)
    {
        puts("opción");
    }
    puts("chau");
}

int signo(int x)
{
    if (0)
    {
        return 99;
    }
    switch (x)
    {
    case 0:
        return 0;
    default:
        break;
    }
    if (x > 0) return 1; else return -1;
}

int bien(int n)
{
    int s = 0;
    for (int i = 0; i < n; i++)
    {
        if (i % 2 == 0)
            continue;
        s += i;
    }
    while (1)
    {
        if (s > 100)
            break;
        s *= 2;
    }
    do { s--; } while (s > 50);
    return s;
}

char leer(void)
{
    char c = '\\0';
    do
    {
        char c = getchar();
        printf("%c", c);
    } while (c == 'n');
    return c;
}
"""


@pytest.fixture
def archivo(tmp_path: Path) -> Path:
    ruta = tmp_path / "flujo.c"
    ruta.write_text(FUENTE, encoding="utf-8")
    return ruta


def _hallazgos(archivo):
    return {f.nombre: [(h.codigo, h.severidad, h.linea) for h in f.hallazgos] for f in cfg_de_archivo(archivo)}


def test_codigo_inalcanzable_y_bucles(archivo):
    assert _hallazgos(archivo) == {
        "buscar": [("GIG001", "advertencia", 11), ("GIG001", "advertencia", 15)],
        "sumar_hasta": [("GIG002", "advertencia", 21)],
        "menu": [("GIG002", "error", 30), ("GIG001", "advertencia", 34)],
        "signo": [("GIG001", "advertencia", 41)],
        "bien": [],  # continue, break del propio lazo y do-while que avanza: sin falsos positivos
        "leer": [("GIG002", "advertencia", 75)],
    }


def test_la_variable_tapada_se_explica(archivo):
    leer = next(f for f in cfg_de_archivo(archivo) if f.nombre == "leer")
    assert "declara otra variable c que tapa" in leer.hallazgos[0].mensaje
    assert "(c = …)" in leer.hallazgos[0].sugerencia


def test_el_texto_viene_del_fuente(archivo):
    buscar = next(f for f in cfg_de_archivo(archivo) if f.nombre == "buscar")
    textos = [t for b in buscar.bloques for _, t in b.sentencias]
    assert 'printf("encontrado\\n");' in textos and "i++" in textos and "int i = 0;" in textos
    assert not buscar.bloques[0].sentencias  # la entrada no tiene sentencias


def test_mermaid_marca_muertos_e_infinitos(archivo):
    texto = mermaid(cfg_de_archivo(archivo))
    assert texto.startswith("flowchart TD")
    assert 'subgraph buscar_fn ["buscar()"]' in texto
    assert "-->|V|" in texto and "-->|F|" in texto
    assert "classDef muerto" in texto and "class menu_" in texto and " infinito" in texto


def test_cli(archivo, tmp_path):
    res = runner.invoke(app, ["cfg", str(archivo), "-f", "json"])
    assert res.exit_code == 1  # hay un while (1) sin salida
    datos = json.loads(res.stdout)
    assert {h["codigo"] for h in datos["hallazgos"]} == {"GIG001", "GIG002"}
    res = runner.invoke(app, ["cfg", str(archivo), "--funcion", "bien", "-f", "texto"])
    assert res.exit_code == 0 and "sin código inalcanzable" in res.stdout
    assert runner.invoke(app, ["cfg", str(archivo), "--funcion", "nada"]).exit_code == 2
