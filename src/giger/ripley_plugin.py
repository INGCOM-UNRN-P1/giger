"""Plugin de GIGER para integración con RIPLEY."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from giger.core.graph import analizar_callgraph_archivo


class GigerPlugin:
    """Plugin de generación de callgraphs y detección de funciones muertas para Ripley."""

    name = "callgraph"
    version = "0.1.0"

    def is_available(self) -> bool:
        return True

    def execute(self, workspace: Path, manifest_config: Dict[str, Any]) -> Dict[str, Any]:
        archivos = list(workspace.glob("*.c")) + list(workspace.glob("src/*.c"))
        observaciones = []
        total_fns = 0

        for a in archivos:
            cg = analizar_callgraph_archivo(a)
            total_fns += len(cg.funciones)
            for h in cg.funciones_huerfanas:
                observaciones.append({
                    "codigo": "DEAD_FUNCTION",
                    "severidad": "WARNING",
                    "archivo": str(a),
                    "mensaje": f"Función '{h}' declarada pero nunca invocada en el código.",
                })

        return {
            "ok": True,
            "total_funciones": total_fns,
            "observaciones": observaciones,
        }
