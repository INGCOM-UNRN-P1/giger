# 🕸️ GIGER — Generador de Mapas de Llamadas y Grafos de Control en C

> 📖 **Manual de Usuario:** Para una guía exhaustiva de comandos, banderas, arquitectura y ejemplos, consultá el [Manual de Uso](MANUAL.md).

GIGER analiza el código fuente en C para construir el mapa estático de llamadas entre funciones (Call Graph), detectar ciclos recursivos, funciones no invocadas (*dead code*) y exportar diagramas en sintaxis Mermaid.

---

## 🎯 Alcance

### Qué cubre
- Análisis estático de la topología de llamadas en código fuente C.
- Extracción y renderizado de mapas de llamadas entre funciones (Call Graphs).
- Detección de código muerto: una función es *huérfana* si ninguna otra función **del mismo archivo** la invoca (excepto `main`). El análisis es intra-archivo: una función definida en un `.c` y usada desde otro se reporta como huérfana. Con `--fail-on-orphans` el comando sale con código 1 si hay huérfanas (por defecto siempre 0).
- Exportación de diagramas a sintaxis Mermaid.

### Qué no cubre (Límites y Delegación)
- Grafos de flujo de control (CFG) intra-función, complejidad ciclomática de McCabe ni exportación a DOT/Graphviz: no están implementados.
- Medición dinámica de profundidad de pila en funciones recursivas (delegado a `sebastian`).
- Desensamblado de código máquina ni inspección de jump tables (delegado a `rachel`).
- Perfilado de tiempos de ejecución o ciclos de clock (delegado a `ferro`).

---

## 📋 Requisitos

### Requisitos de Sistema y Entorno
- Multiplataforma. Python >= 3.10.

### Dependencias Externas y Binarios
- `graphviz` (`dot`, opcional para renderizar gráficos vectoriales).

### Integración en el Ecosistema
- CLI `giger`. Plugin registrado en `ripley.plugins` (`callgraph`).

---

## Uso Rápido

```bash
# 1. Analizar e imprimir mapa de llamadas
giger callgraph main.c

# 2. Exportar diagrama en sintaxis Mermaid
giger callgraph main.c --mermaid

# 3. Salida estructurada JSON
giger callgraph main.c --json
```
