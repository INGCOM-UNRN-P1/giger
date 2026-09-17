"""Motor de construcción de grafos de llamadas y detección de recursión en GIGER."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from giger.core.models import AristaLlamada, CallgraphInfo


def _eliminar_comentarios(texto: str) -> str:
    """Blanquea comentarios y literales preservando offsets y saltos de línea.

    Los literales importan tanto como los comentarios: sin enmascararlos, una
    cadena como `"llamar a procesar(x)"` agrega una arista falsa al grafo de
    llamadas, y el `printf("...")` de cualquier mensaje de ayuda basta para
    inventar funciones que nadie invoca.
    """
    resultado = []
    i = 0
    n = len(texto)

    while i < n:
        c = texto[i]
        par = texto[i:i + 2]

        if par == "//":
            fin = texto.find("\n", i)
            fin = n if fin == -1 else fin
        elif par == "/*":
            fin = texto.find("*/", i + 2)
            fin = n if fin == -1 else fin + 2
        elif c in ('"', "'"):
            j = i + 1
            while j < n:
                if texto[j] == "\\":
                    j += 2
                    continue
                if texto[j] == c or texto[j] == "\n":
                    j += 1 if texto[j] == c else 0
                    break
                j += 1
            fin = j
        else:
            resultado.append(c)
            i += 1
            continue

        resultado.append("".join("\n" if ch == "\n" else " " for ch in texto[i:fin]))
        i = fin

    return "".join(resultado)


def analizar_callgraph_archivo(archivo: Path) -> CallgraphInfo:
    """Construye el grafo de llamadas del archivo C."""
    archivo = Path(archivo)
    if not archivo.is_file():
        return CallgraphInfo(archivo=archivo)

    try:
        contenido = archivo.read_text(encoding="utf-8")
    except Exception:
        return CallgraphInfo(archivo=archivo)

    codigo_limpio = _eliminar_comentarios(contenido)

    # 1. Extraer cabeceras de funciones
    re_fn = re.compile(r"^\s*(?:[a-zA-Z0-9_*]+\s+)+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*\{", re.MULTILINE)
    funciones_info: List[Tuple[str, str, int]] = []

    for m in re_fn.finditer(codigo_limpio):
        fn_name = m.group(1)
        if fn_name in ("if", "for", "while", "switch"):
            continue

        start_pos = m.end() - 1
        line_start = codigo_limpio[:m.start()].count("\n") + 1

        brace_count = 0
        end_pos = start_pos
        for i in range(start_pos, len(codigo_limpio)):
            if codigo_limpio[i] == '{':
                brace_count += 1
            elif codigo_limpio[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i
                    break

        cuerpo = codigo_limpio[start_pos:end_pos + 1]
        funciones_info.append((fn_name, cuerpo, line_start))

    nombres_funciones = set(f[0] for f in funciones_info)
    aristas: List[AristaLlamada] = []
    recursivas: Set[str] = set()
    invocadas: Set[str] = set()

    for fn_origen, cuerpo, l_start in funciones_info:
        for fn_destino in nombres_funciones:
            patron_call = re.compile(rf"\b{fn_destino}\s*\(")
            for cm in patron_call.finditer(cuerpo):
                line_call = l_start + cuerpo[:cm.start()].count("\n")
                es_rec = (fn_origen == fn_destino)
                if es_rec:
                    recursivas.add(fn_origen)
                else:
                    invocadas.add(fn_destino)

                aristas.append(AristaLlamada(
                    origen=fn_origen,
                    destino=fn_destino,
                    linea=line_call,
                    es_recursiva=es_rec,
                ))

    # Detectar funciones no invocadas (huérfanas / dead code) excepto main
    huerfanas = [f for f in sorted(nombres_funciones) if f not in invocadas and f != "main"]

    # Generar diagrama Mermaid
    mermaid_lines = ["graph TD"]
    for fn in sorted(nombres_funciones):
        if fn == "main":
            mermaid_lines.append(f'    {fn}(["{fn}() (Entrypoint)"])')
        elif fn in recursivas:
            mermaid_lines.append(f'    {fn}{{"{fn}() (Recursiva)"}}')
        elif fn in huerfanas:
            mermaid_lines.append(f'    {fn}[/"{fn}() (No invocada)"/]')
        else:
            mermaid_lines.append(f'    {fn}["{fn}()"]')

    # Aristas únicas
    aristas_set = set((a.origen, a.destino, a.es_recursiva) for a in aristas)
    for orig, dest, es_rec in sorted(aristas_set):
        estilo = "== recursión ==>" if es_rec else "-->"
        mermaid_lines.append(f'    {orig} {estilo} {dest}')

    return CallgraphInfo(
        archivo=archivo,
        funciones=sorted(nombres_funciones),
        aristas=aristas,
        funciones_recursivas=sorted(recursivas),
        funciones_huerfanas=sorted(huerfanas),
        diagrama_mermaid="\n".join(mermaid_lines),
    )
