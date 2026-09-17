"""Regresión de GIGER-D0301: los literales no deben generar aristas falsas."""

from pathlib import Path

from giger.core.graph import _eliminar_comentarios, analizar_callgraph_archivo

FUENTE = """#include <stdio.h>
void real(void) { }
void nunca_llamada(void) { }
int main(void) {
    /* llamada en comentario: fantasma(); */
    printf("mensaje con nunca_llamada() adentro\\n");
    const char *s = "otra fantasma()";
    real();
    return 0;
}
"""


def _info(tmp_path):
    ruta = tmp_path / "caso.c"
    ruta.write_text(FUENTE, encoding="utf-8")
    return analizar_callgraph_archivo(ruta)


def test_no_hay_aristas_desde_literales_ni_comentarios(tmp_path):
    aristas = {(a.origen, a.destino) for a in _info(tmp_path).aristas}
    assert aristas == {("main", "real")}


def test_una_llamada_dentro_de_un_string_no_tapa_codigo_muerto(tmp_path):
    """`nunca_llamada()` aparece solo dentro de un printf: sigue siendo huérfana."""
    assert "nunca_llamada" in _info(tmp_path).funciones_huerfanas


def test_el_enmascarado_preserva_offsets():
    enmascarado = _eliminar_comentarios(FUENTE)
    assert len(enmascarado) == len(FUENTE)
    assert enmascarado.count("\n") == FUENTE.count("\n")
