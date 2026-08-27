"""Tests unitarios para el generador de callgraphs en GIGER."""

from pathlib import Path
import pytest
from giger.core.graph import analizar_callgraph_archivo


def test_callgraph_con_recursion_y_huerfanas(tmp_path):
    fuente = tmp_path / "grafo.c"
    fuente.write_text("""
    #include <stdio.h>

    void funcion_muerta(void) {
        printf("Nunca llamada\\n");
    }

    int fibonacci(int n) {
        if (n <= 1) return n;
        return fibonacci(n - 1) + fibonacci(n - 2);
    }

    int main(void) {
        fibonacci(5);
        return 0;
    }
    """)

    cg = analizar_callgraph_archivo(fuente)
    assert "main" in cg.funciones
    assert "fibonacci" in cg.funciones
    assert "funcion_muerta" in cg.funciones
    assert "fibonacci" in cg.funciones_recursivas
    assert "funcion_muerta" in cg.funciones_huerfanas
    assert "graph TD" in cg.diagrama_mermaid
