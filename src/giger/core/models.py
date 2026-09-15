"""Modelos de datos para el análisis de grafos de llamadas y CFG en GIGER."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set


@dataclass
class AristaLlamada:
    origen: str
    destino: str
    linea: int
    es_recursiva: bool = False


@dataclass
class CallgraphInfo:
    archivo: Path
    funciones: List[str] = field(default_factory=list)
    aristas: List[AristaLlamada] = field(default_factory=list)
    funciones_recursivas: List[str] = field(default_factory=list)
    funciones_huerfanas: List[str] = field(default_factory=list)
    diagrama_mermaid: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "archivo": str(self.archivo),
            "total_funciones": len(self.funciones),
            "total_llamadas": len(self.aristas),
            "funciones": self.funciones,
            "funciones_recursivas": self.funciones_recursivas,
            "funciones_huerfanas": self.funciones_huerfanas,
            "diagrama_mermaid": self.diagrama_mermaid,
        }
