# Manual de Uso y Referencia Técnica: giger

> **GIGER** — Generador de mapas de llamadas (Call Graphs) y detección de recursión y código muerto en C
> **Versión:** `0.1.0` · **CLI principal:** `giger` · **Plugin Ripley:** `callgraph`

---

## 1. Arquitectura y Propósito Pedagógico

`giger` forma parte del ecosistema de herramientas de la cátedra de Programación 1 (UNRN). Su objetivo central es resolver de forma modular, determinista y automatizada las tareas asociadas a su dominio específico dentro del ciclo de desarrollo, evaluación y aprendizaje de software en C.

### Alcance Funcional (Qué cubre)
- Análisis estático de la topología de llamadas en código fuente C.
- Extracción y renderizado de mapas de llamadas entre funciones (Call Graphs).
- Detección de código muerto: una función es *huérfana* si ninguna otra función **del mismo archivo** la invoca (excepto `main`). El análisis es intra-archivo: una función definida en un `.c` y usada desde otro se reporta como huérfana. Con `--fail-on-orphans` el comando sale con código 1 si hay huérfanas (por defecto siempre 0).
- Exportación de diagramas a sintaxis Mermaid.

### Límites de Responsabilidad y Delegación (Qué no cubre)
- Grafos de flujo de control (CFG) intra-función, complejidad ciclomática de McCabe ni exportación a DOT/Graphviz: no están implementados.
- Medición dinámica de profundidad de pila en funciones recursivas (delegado a `sebastian`).
- Desensamblado de código máquina ni inspección de jump tables (delegado a `rachel`).
- Perfilado de tiempos de ejecución o ciclos de clock (delegado a `ferro`).

### Principios de Diseño
- **Enfoque Pedagógico:** Diagnósticos y mensajes en español rioplatense orientados a facilitar la comprensión de errores conceptuales.
- **Salida Estructurada Dual:** Soporte nativo para visualización enriquecida en terminal (Rich) y salida parseable para orquestadores (`--json`).
- **Integración Contractual:** Capacidad de emitir secciones de reporte para `dredd` (`dredd-section`) y actuar como satélite orquestado por `ripley`.
- **Idempotencia y Robustez:** Validación de precondiciones y comandos de autodiagnóstico (`doctor`) para verificación del entorno.

---

## 2. Instalación y Requisitos

### Requisitos del Sistema
- **Python:** `>= 3.10` (recomendado Python 3.11 o 3.12).
- **Gestor de paquetes:** [`uv`](https://github.com/astral-sh/uv) (entorno estándar de cátedra).
- **Toolchain C (si aplica):** GCC / Clang, Make, GDB y bibliotecas estándar de desarrollo.

### Instalación en el Entorno de Usuario
Para instalar la herramienta de forma global y aislada en el sistema mediante `uv tool`:
```bash
uv tool install --editable /home/mrtin/dev/tools/giger
```

### Verificación de Instalación
Ejecutá el comando `doctor` para constatar que todas las dependencias y binarios requeridos estén presentes y operativos:
```bash
giger doctor
```

---

## 3. Guía Integral de Comandos (CLI)

| Comando | Descripción Breve |
| :--- | :--- |
| [`giger check`](#check) | Construye el mapa de llamadas entre funciones y detecta recursión y código muerto. |
| [`giger callgraph`](#callgraph) | Construye el mapa de llamadas entre funciones y detecta recursión y código muerto. |
| [`giger report`](#report) | Genera directamente la sección de reporte Markdown de GIGER para Dredd. |
| [`giger doctor`](#doctor) | Verifica el estado del entorno de análisis de grafos de llamadas GIGER (Python, GCC, cflow). |

### `giger check`

Construye el mapa de llamadas entre funciones y detecta recursión y código muerto.

Códigos de salida: 0 análisis correcto, 2 archivo inexistente y, solo con
--fail-on-orphans, 1 si hay funciones huérfanas.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `fuente` | `Path` | Archivo C a analizar. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--mermaid`, `-m` | `bool` | `False` | Emitir diagrama en sintaxis Mermaid. |
| `--json` | `bool` | `False` | Salida en JSON. |
| `--md`, `--output-md`, `-o` | `Optional[Path]` | `None` | Generar sección de reporte en formato Markdown para fusión en Dredd. |
| `--fail-on-orphans` | `bool` | `False` | Salir con código 1 si hay funciones huérfanas (por defecto siempre 0). |

#### Ejemplo de Invocación
```bash
giger check <fuente>
```

### `giger callgraph`

Construye el mapa de llamadas entre funciones y detecta recursión y código muerto.

Códigos de salida: 0 análisis correcto, 2 archivo inexistente y, solo con
--fail-on-orphans, 1 si hay funciones huérfanas.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `fuente` | `Path` | Archivo C a analizar. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--mermaid`, `-m` | `bool` | `False` | Emitir diagrama en sintaxis Mermaid. |
| `--json` | `bool` | `False` | Salida en JSON. |
| `--md`, `--output-md`, `-o` | `Optional[Path]` | `None` | Generar sección de reporte en formato Markdown para fusión en Dredd. |
| `--fail-on-orphans` | `bool` | `False` | Salir con código 1 si hay funciones huérfanas (por defecto siempre 0). |

#### Ejemplo de Invocación
```bash
giger callgraph <fuente>
```

### `giger report`

Genera directamente la sección de reporte Markdown de GIGER para Dredd.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `fuente` | `Path` | Archivo C a analizar. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--output`, `-o` | `Optional[Path]` | `None` | Ruta de destino del archivo Markdown. |

#### Ejemplo de Invocación
```bash
giger report <fuente>
```

### `giger doctor`

Verifica el estado del entorno de análisis de grafos de llamadas GIGER (Python, GCC, cflow).

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--json` | `bool` | `False` | Emitir diagnóstico en formato JSON estructurado. |

#### Ejemplo de Invocación
```bash
giger doctor
```

---

## 4. Formatos de Salida e Integración con el Ecosistema

### Modo Interactivo / Terminal (Rich)
Por defecto, la herramienta renderiza paneles, árboles y tablas estilizadas para facilitar la lectura del estudiante y docente en terminales modernas con soporte ANSI.

### Modo Estructurado JSON (`--json`)
Para integración con pipelines de CI/CD, scripts de automatización u orquestadores externos, la opción `--json` emite un documento JSON estricto por la salida estándar (`stdout`), dirigiendo cualquier mensaje de logging a `stderr`:
```bash
giger check --json
```

### Integración con Dredd (`dredd-section`)
Cuando la herramienta genera reportes de evaluación para entregas de alumnos, produce una sección Markdown estandarizada conforme al contrato de integración de Dredd (v1.0.0):
```markdown
<!-- dredd-section: giger, tool=giger, version=0.1.0, status=ok -->
```
Este encabezado garantiza la agregación determinista de los hallazgos en la rúbrica docente.

### Integración con Ripley
`giger` está registrada en el catálogo de plugins satélites de Ripley (`SATELLITE_CATALOG`). Puede invocarse directamente a través del motor de evaluación de Ripley configurando el análisis en `ripley.toml`.

---

## 5. Diagnóstico y Códigos de Salida

### Códigos de Retorno (`exit code`)
| Código | Significado |
| :---: | :--- |
| `0` | Ejecución exitosa sin hallazgos críticos ni errores de sintaxis. |
| `1` | Hallazgos pedagógicos detectados, infracción de reglas o advertencias activas. |
| `2` | Error de sintaxis en argumentos CLI o archivo fuente no encontrado. |
| `>2` | Error no recuperable del sistema, fallo de memoria o excepción interna. |

### Diagnóstico del Entorno (`doctor`)
Ante comportamientos inesperados, verificá el estado operativo con:
```bash
giger doctor
```
Comprueba la presencia de las dependencias requeridas y la integridad de los componentes del paquete.