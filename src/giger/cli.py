"""CLI de GIGER — Generador de grafos de flujo y mapas de llamadas en C."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from giger import __version__
from giger.core.graph import analizar_callgraph_archivo

console = Console()
err_console = Console(stderr=True)

app = typer.Typer(
    name="giger",
    help="🕸️ GIGER — Generador de grafos de flujo de control (CFG) y mapas de llamadas (Call Graphs) en C.",
    add_completion=True,
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold cyan]GIGER[/bold cyan] versión [bold]{__version__}[/bold]")
        raise typer.Exit(code=0)


@app.callback()
def main_callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Muestra la versión de GIGER.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    pass


@app.command("callgraph")
def callgraph_cmd(
    fuente: Path = typer.Argument(..., help="Archivo C a analizar."),
    mermaid_view: bool = typer.Option(False, "--mermaid", "-m", help="Emitir diagrama en sintaxis Mermaid."),
    json_output: bool = typer.Option(False, "--json", help="Salida en JSON."),
) -> None:
    """Construye el mapa de llamadas entre funciones y detecta recursión y código muerto."""
    if not fuente.is_file():
        err_console.print(f"[red]Error:[/red] No se encontró el archivo '{fuente}'.")
        raise typer.Exit(code=2)

    cg = analizar_callgraph_archivo(fuente)

    if json_output:
        print(json.dumps(cg.to_dict(), indent=2, ensure_ascii=False))
        raise typer.Exit(code=0)

    if mermaid_view:
        console.print(cg.diagrama_mermaid)
        raise typer.Exit(code=0)

    tabla = Table(title=f"Mapa de Llamadas en {fuente.name} ({len(cg.funciones)} funciones)")
    tabla.add_column("Función", style="bold cyan")
    tabla.add_column("Tipo", justify="center")
    tabla.add_column("Llama a", style="green")

    for fn in cg.funciones:
        llamadas_a = [a.destino for a in cg.aristas if a.origen == fn]
        tipo = "[bold magenta]Recursiva[/bold magenta]" if fn in cg.funciones_recursivas else "[dim]Huérfana[/dim]" if fn in cg.funciones_huerfanas else "Normal"
        dest_str = ", ".join(sorted(set(llamadas_a))) if llamadas_a else "[dim]—[/dim]"
        tabla.add_row(f"{fn}()", tipo, dest_str)

    console.print(tabla)

    if cg.funciones_recursivas:
        console.print(f"[magenta]• Funciones recursivas:[/magenta] {', '.join(cg.funciones_recursivas)}")
    if cg.funciones_huerfanas:
        console.print(f"[yellow]• Funciones no invocadas (candidatas a dead code):[/yellow] {', '.join(cg.funciones_huerfanas)}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
