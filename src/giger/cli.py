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


def generar_seccion_markdown(cg) -> str:
    """Genera sección de mapa de llamadas y código muerto para Dredd."""
    lines = ["## Grafo de Llamadas y Funciones (Giger)\n"]
    lines.append(f"- **Archivo analizado:** `{cg.archivo.name}`")
    lines.append(f"- **Funciones detectadas:** {len(cg.funciones)}")
    lines.append(f"- **Funciones recursivas:** {len(cg.funciones_recursivas)}")
    lines.append(f"- **Funciones huérfanas / dead code:** {len(cg.funciones_huerfanas)}\n")
    if cg.funciones_huerfanas:
        lines.append(f"> [!WARNING]\n> **Código Muerto Potencial:** Las funciones {', '.join(f'`{f}()`' for f in cg.funciones_huerfanas)} nunca son invocadas desde `main()`.\n")
    else:
        lines.append("> [!TIP]\n> **Estructura Conexa:** Todas las funciones del módulo son alcanzables desde el flujo de ejecución.\n")

    if cg.funciones:
        lines.append("| Función | Tipo | Invoca a |")
        lines.append("| :--- | :---: | :--- |")
        for fn in cg.funciones:
            llamadas_a = [a.destino for a in cg.aristas if a.origen == fn]
            tipo = "Recursiva" if fn in cg.funciones_recursivas else "Huérfana" if fn in cg.funciones_huerfanas else "Normal"
            dest_str = ", ".join(f"`{d}()`" for d in sorted(set(llamadas_a))) if llamadas_a else "—"
            lines.append(f"| `{fn}()` | {tipo} | {dest_str} |")
        lines.append("")

    if cg.diagrama_mermaid:
        lines.append("### Call Graph (Mermaid)")
        lines.append("```mermaid")
        lines.append(cg.diagrama_mermaid)
        lines.append("```\n")
    return "\n".join(lines)


@app.command("callgraph")
@app.command("check")
def callgraph_cmd(
    fuente: Path = typer.Argument(..., help="Archivo C a analizar."),
    mermaid_view: bool = typer.Option(False, "--mermaid", "-m", help="Emitir diagrama en sintaxis Mermaid."),
    json_output: bool = typer.Option(False, "--json", help="Salida en JSON."),
    output_md: Optional[Path] = typer.Option(None, "--md", "--output-md", "-o", help="Generar sección de reporte en formato Markdown para fusión en Dredd."),
) -> None:
    """Construye el mapa de llamadas entre funciones y detecta recursión y código muerto."""
    if not fuente.is_file():
        err_console.print(f"[red]Error:[/red] No se encontró el archivo '{fuente}'.")
        raise typer.Exit(code=2)

    cg = analizar_callgraph_archivo(fuente)

    if output_md:
        md_text = generar_seccion_markdown(cg)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(md_text, encoding="utf-8")
        console.print(f"[green]✓ Sección Markdown generada en:[/green] [cyan]{output_md}[/cyan]")
        raise typer.Exit(code=0)

    if json_output:
        print(json.dumps(cg.to_dict(), indent=2, ensure_ascii=False))
        raise typer.Exit(code=0)

    if mermaid_view:
        if cg.diagrama_mermaid:
            console.print(cg.diagrama_mermaid, markup=False)
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


@app.command("report")
def report_cmd(
    fuente: Path = typer.Argument(..., help="Archivo C a analizar."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Ruta de destino del archivo Markdown."),
) -> None:
    """Genera directamente la sección de reporte Markdown de GIGER para Dredd."""
    if not fuente.is_file():
        err_console.print(f"[red]Error:[/red] No se encontró el archivo '{fuente}'.")
        raise typer.Exit(code=2)
    cg = analizar_callgraph_archivo(fuente)
    md_content = generar_seccion_markdown(cg)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(md_content, encoding="utf-8")
        console.print(f"[green]✓ Reporte Markdown generado en:[/green] [cyan]{output}[/cyan]")
    else:
        print(md_content)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
