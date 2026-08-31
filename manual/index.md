---
title: "Manual de Referencia: giger"
subtitle: "Giger — Generador de Grafos de Control de Flujo (CFG), Grafo de Llamadas y Dead Code"
author: "Cátedra de Algoritmos y Programación"
date: "2026-08-31"
---

(manual-giger)=
# Giger — Generador de Grafos de Control de Flujo (CFG), Grafo de Llamadas y Dead Code

````{abstract}
**Rol en el ecosistema:** Análisis estructural de código C para generar grafos de llamadas entre funciones, grafos de flujo de control (CFG), detección de lazos infinitos y funciones muertas no invocadas.
````

---

(manual-giger-proposito)=
## 1. Propósito y Filosofía Pedagógica

La herramienta **`giger`** forma parte del ecosistema oficial de software de la cátedra. Su diseño sigue principios pedagógicos rigurosos:

1. **Evidencia Técnica Directa**: Todo diagnóstico se fundamenta en la norma ISO C (C11/C23), en el modelo de memoria del sistema o en convenciones arquitectónicas formales.
2. **Acción Correctiva Concreta**: Cada advertencia incluye la prescripción técnica inmediata para resolver el defecto sin recurrir a conjeturas.
3. **Autonomía del Estudiante**: Facilita la autoevaluación local antes de la entrega final del trabajo práctico.
4. **Objetividad Docente**: Estandariza la corrección automática eliminando discrepancias subjetivas en la evaluación.

---

(manual-giger-instalacion)=
## 2. Instalación y Diagnóstico del Entorno

````{important}
Asegurate de contar con el compilador GCC/Clang y las librerías del sistema instaladas antes de ejecutar `giger`.
````

Para comprobar el estado de salud de tu entorno de trabajo y las dependencias auxiliares:

````{code-block} bash
# Comprobación de dependencias del sistema
giger doctor
````

Si se detecta la falta de alguna utilidad (como `gdb`, `valgrind`, `clang-format` o `typst`), el comando indicará el paquete exacto a instalar según tu distribución GNU/Linux o entorno MSYS2.

---

(manual-giger-comandos)=
## 3. Referencia Completa de Comandos CLI

A continuación se detallan los subcomandos principales disponibles en `giger`:

| Sintaxis del Comando | Descripción y Efecto |
| :--- | :--- |
| `giger callgraph src/ -o grafo.dot` | Genera el Call Graph del proyecto en formato DOT/Graphviz. |
| `giger cfg <archivo.c> --function <fn>` | Genera el grafo de flujo de control (CFG) de una función. |
| `giger dead-code src/` | Detecta funciones estáticas o públicas que nunca son invocadas. |
| `giger cycles src/` | Identifica ciclos de recursión directa o indirecta entre módulos. |

````{tip}
Podés agregar el flag `--json` a la mayoría de los comandos para exportar resultados en formato estructurado o `--md` para generar reportes Markdown para el informe de entrega.
````

---

(manual-giger-tutorial)=
## 4. Tutorial Paso a Paso con Ejemplos Reales

### Caso de Estudio

Considerá el siguiente fragmento de código representativo:

````{code-block} c
:linenos:
#include <stdio.h>

void funcion_muerta(void) {
    printf("Nunca se ejecuta\n");
}

void procesar(int x) {
    if (x > 0) {
        printf("Positivo\n");
    } else {
        printf("No positivo\n");
    }
}

int main(void) {
    procesar(10);
    return 0;
}
````

### Ejecución de la Herramienta

Ejecutá el análisis desde tu terminal:

````{code-block} bash
giger callgraph src/ -o grafo.dot
````

### Salida Obtenida en Consola

````{code-block} text
[!] GIGER DEAD CODE DETECTED:
    • 'funcion_muerta()' en src/main.c:3 no tiene llamadores en el Call Graph.

[✓] CFG de 'procesar()': 4 bloques básicos, 2 ramas condicionales (Complejidad ciclomática: 2).
[✓] Grafo de llamadas exportado a 'grafo.dot'.
````

````{note}
Prestá atención a la explicación pedagógica generada: la herramienta no solo señala la línea del problema, sino que explica la causa raíz y el impacto en memoria o arquitectura.
````

---

(manual-giger-ejercicios)=
## 5. Ejercicios Prácticos y Desafíos

Practicá el uso avanzado de **`giger`** resolviendo los siguientes ejercicios:

````{exercise} Desafío 1: Detección de Funciones Obsoletas
Identificar funciones huérfanas en un TDA de gran tamaño.

**Instrucción de ejecución:**
```bash
giger dead-code src/
```
````

````{solution} Desafío 1
```bash
giger dead-code src/
# Verificá que la operación concluya exitosamente con código de salida 0.
```
````

````{exercise} Desafío 2: Renderizado de Call Graph a PNG
Convertir el grafo DOT de llamadas a imagen con Graphviz.

**Instrucción de ejecución:**
```bash
giger callgraph src/ -o callgraph.dot && dot -Tpng callgraph.dot -o callgraph.png
```
````

````{solution} Desafío 2
```bash
giger callgraph src/ -o callgraph.dot && dot -Tpng callgraph.dot -o callgraph.png
# Revisá el archivo generado o el informe en terminal para confirmar la resolución del problema.
```
````

````{exercise} Desafío 3: Análisis de Ciclos de Recursión Cruzada
Verificar si la función A llama a B y B llama a A.

**Instrucción de ejecución:**
```bash
giger cycles src/
```
````

````{solution} Desafío 3
```bash
giger cycles src/
# Comprobá que la salida confirme la ausencia de advertencias o errores pendientes.
```
````

---

(manual-giger-makefile)=
## 6. Integración en el Flujo de Trabajo y Makefile

Para incorporar `giger` de forma automática a tu flujo de desarrollo, agregá la siguiente regla en el `Makefile` de tu proyecto:

````{code-block} makefile
check-giger:
	@echo "=== Ejecutando verificación con giger ==="
	giger check src/ include/

.PHONY: check-giger
````

Ejecutá `make check-giger` antes de cada commit para asegurar que tu código conserve el estado de aprobación.
