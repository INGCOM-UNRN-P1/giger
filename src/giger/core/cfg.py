"""Grafo de flujo de control (CFG) de cada función C, con código inalcanzable y bucles infinitos (Ola 19).

`giger cfg archivo.c` arma, por función, los bloques básicos (sentencias que se ejecutan siempre juntas)
y las aristas entre ellos, desde el AST de tree-sitter:

- **Código inalcanzable** (`GIG001`): un bloque al que no llega ninguna arista desde la entrada: lo que
  sigue a un `return`, `break`, `continue`, `goto` o `exit()` en el mismo bloque, o la rama de una
  condición constante (`if (0)`, el `else` de `if (1)`, lo que sigue a un `while (1)` sin salida).
- **Bucle infinito trivial** (`GIG002`): un lazo cuya condición es siempre verdadera (`while (1)`,
  `for (;;)`) y no tiene `break`, `return`, `goto` ni `exit()` que lo termine; o uno cuya condición
  usa sólo variables locales que el cuerpo no modifica (ni por asignación, ni `++`/`--`, ni pasando su
  dirección). Es lo que un estudiante escribe cuando olvida el `i++`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import tree_sitter_c as tsc
from tree_sitter import Language, Node, Parser

_PARSER: Optional[Parser] = None
_TERMINAN = {"exit", "abort", "_Exit", "quick_exit"}


def _parser() -> Parser:
    global _PARSER
    if _PARSER is None:
        _PARSER = Parser(Language(tsc.language()))
    return _PARSER


_ORIGINAL: List[bytes] = [b""]  # el fuente del archivo que se está procesando


def _texto(nodo: Optional[Node]) -> str:
    if nodo is None:
        return ""
    return _ORIGINAL[0][nodo.start_byte:nodo.end_byte].decode("utf-8", errors="replace")


def _recorrer(nodo: Node):
    yield nodo
    for hijo in nodo.children:
        yield from _recorrer(hijo)


@dataclass
class Bloque:
    id: int
    tipo: str = "normal"  # entrada, salida, condicion, normal
    sentencias: List[Tuple[int, str]] = field(default_factory=list)  # (línea, texto)
    sucesores: List[Tuple[int, str]] = field(default_factory=list)  # (destino, etiqueta)

    @property
    def lineas(self) -> Tuple[int, int]:
        lineas = [n for n, _ in self.sentencias]
        return (min(lineas), max(lineas)) if lineas else (0, 0)


@dataclass
class HallazgoCFG:
    codigo: str
    severidad: str
    funcion: str
    linea: int
    mensaje: str
    sugerencia: str


@dataclass
class CFGFuncion:
    nombre: str
    linea: int
    bloques: List[Bloque]
    alcanzables: Set[int]
    hallazgos: List[HallazgoCFG] = field(default_factory=list)
    bucles_infinitos: Set[int] = field(default_factory=set)  # ids de los bloques de condición


def _constante(cond: Optional[Node]) -> Optional[bool]:
    """True/False si la condición es un literal (`1`, `0`, `true`); None si depende de algo."""
    if cond is None:
        return True  # `for (;;)`
    while cond.type == "parenthesized_expression" and cond.named_child_count == 1:
        cond = cond.named_children[0]
    texto = _texto(cond).strip()
    if cond.type == "number_literal":
        try:
            return int(texto.rstrip("uUlL"), 0) != 0
        except ValueError:
            return None
    if cond.type in ("true", "false") or texto in ("true", "false"):
        return texto == "true"
    return None


class _Constructor:
    def __init__(self, nombre: str) -> None:
        self.nombre = nombre
        self.bloques: List[Bloque] = []
        self.entrada = self._nuevo("entrada")
        self.salida = self._nuevo("salida")
        self.lazos: List[Tuple[Bloque, Bloque]] = []  # (destino del break, destino del continue)
        self.salidas_de_switch: List[Bloque] = []
        self.etiquetas: Dict[str, Bloque] = {}
        self.hallazgos: List[HallazgoCFG] = []
        self.infinitos: Set[int] = set()

    def _nuevo(self, tipo: str = "normal") -> Bloque:
        b = Bloque(len(self.bloques), tipo)
        self.bloques.append(b)
        return b

    @staticmethod
    def _unir(origen: Optional[Bloque], destino: Bloque, etiqueta: str = "") -> None:
        if origen is not None:
            origen.sucesores.append((destino.id, etiqueta))

    def _actual(self, actual: Optional[Bloque]) -> Bloque:
        # Sin un bloque actual (después de un return) lo que sigue va a un bloque sin predecesores.
        return actual if actual is not None else self._nuevo()

    def _agregar(self, actual: Optional[Bloque], nodo: Node, texto: Optional[str] = None) -> Bloque:
        b = self._actual(actual)
        if b.tipo == "condicion" or (b.sentencias and b.sucesores):
            nuevo = self._nuevo()
            self._unir(b, nuevo)
            b = nuevo
        b.sentencias.append((nodo.start_point.row + 1, (texto or _texto(nodo)).strip()))
        return b

    def _condicion(self, actual: Optional[Bloque], cond: Optional[Node], texto: str, linea: int) -> Bloque:
        c = self._nuevo("condicion")
        c.sentencias.append((linea, texto))
        self._unir(actual, c)
        return c

    def sentencia(self, nodo: Optional[Node], actual: Optional[Bloque]) -> Optional[Bloque]:
        if nodo is None:
            return actual
        t = nodo.type
        if t == "compound_statement":
            for hijo in nodo.named_children:
                if hijo.type != "comment":
                    actual = self.sentencia(hijo, actual)
            return actual
        if t == "return_statement":
            b = self._agregar(actual, nodo)
            self._unir(b, self.salida)
            return None
        if t in ("break_statement", "continue_statement"):
            b = self._agregar(actual, nodo)
            if t == "break_statement":
                destino = self.salidas_de_switch[-1] if self.salidas_de_switch and (
                    not self.lazos or self._dentro_de_switch(nodo)) else (self.lazos[-1][0] if self.lazos else None)
            else:
                destino = self.lazos[-1][1] if self.lazos else None
            if destino is not None:
                self._unir(b, destino)
            return None
        if t == "goto_statement":
            b = self._agregar(actual, nodo)
            etiqueta = _texto(nodo.child_by_field_name("label"))
            self._unir(b, self.etiquetas.setdefault(etiqueta, self._nuevo()))
            return None
        if t == "labeled_statement":
            etiqueta = _texto(nodo.child_by_field_name("label"))
            destino = self.etiquetas.setdefault(etiqueta, self._nuevo())
            self._unir(actual, destino)
            interna = [c for c in nodo.named_children if c.type != "statement_identifier"]
            return self.sentencia(interna[0], destino) if interna else destino
        if t == "if_statement":
            return self._si(nodo, actual)
        if t in ("while_statement", "for_statement", "do_statement"):
            return self._lazo(nodo, actual)
        if t == "switch_statement":
            return self._switch(nodo, actual)
        if t == "expression_statement" and self._termina(nodo):
            b = self._agregar(actual, nodo)
            self._unir(b, self.salida)
            return None
        if t in ("case_statement",):
            return self._agregar(actual, nodo, _texto(nodo).split(":")[0] + ":")
        return self._agregar(actual, nodo)

    def _dentro_de_switch(self, nodo: Node) -> bool:
        """Si el `break` más cercano corta un switch (y no un lazo más interno)."""
        padre = nodo.parent
        while padre is not None:
            if padre.type == "switch_statement":
                return True
            if padre.type in ("while_statement", "for_statement", "do_statement"):
                return False
            padre = padre.parent
        return False

    @staticmethod
    def _termina(nodo: Node) -> bool:
        llamada = nodo.named_children[0] if nodo.named_children else None
        return (llamada is not None and llamada.type == "call_expression"
                and _texto(llamada.child_by_field_name("function")) in _TERMINAN)

    def _si(self, nodo: Node, actual: Optional[Bloque]) -> Optional[Bloque]:
        cond = nodo.child_by_field_name("condition")
        c = self._condicion(actual, cond, f"if {_texto(cond)}", nodo.start_point.row + 1)
        valor = _constante(cond)
        entonces = self._nuevo()
        if valor is not False:
            self._unir(c, entonces, "V")
        fin_entonces = self.sentencia(nodo.child_by_field_name("consequence"), entonces)
        alternativa = nodo.child_by_field_name("alternative")
        salidas: List[Optional[Bloque]] = [fin_entonces]
        if alternativa is not None:
            otro = self._nuevo()
            if valor is not True:
                self._unir(c, otro, "F")
            cuerpo = alternativa.named_children[-1] if alternativa.type == "else_clause" else alternativa
            salidas.append(self.sentencia(cuerpo, otro))
        unir = self._nuevo()
        if alternativa is None and valor is not True:
            self._unir(c, unir, "F")
        for s in salidas:
            self._unir(s, unir)
        return unir

    def _lazo(self, nodo: Node, actual: Optional[Bloque]) -> Optional[Bloque]:
        t = nodo.type
        cond = nodo.child_by_field_name("condition")
        if t == "for_statement":
            inicial = nodo.child_by_field_name("initializer")
            if inicial is not None:
                actual = self._agregar(actual, inicial)
        valor = _constante(cond)
        texto = {"while_statement": "while", "for_statement": "for", "do_statement": "do … while"}[t]
        linea = nodo.start_point.row + 1
        c = self._nuevo("condicion")
        c.sentencias.append((linea, f"{texto} {_texto(cond) if cond is not None else '(;;)'}".strip()))
        despues = self._nuevo()
        cuerpo_inicio = self._nuevo()
        actualizacion = self._nuevo() if t == "for_statement" else None
        continuar = actualizacion or c
        if t == "do_statement":
            self._unir(actual, cuerpo_inicio)
        else:
            self._unir(actual, c)
        self._unir(c, cuerpo_inicio, "V")
        if valor is not True:
            self._unir(c, despues, "F")
        self.lazos.append((despues, continuar))
        fin = self.sentencia(nodo.child_by_field_name("body"), cuerpo_inicio)
        self.lazos.pop()
        if actualizacion is not None:
            upd = nodo.child_by_field_name("update")
            if upd is not None:
                actualizacion.sentencias.append((upd.start_point.row + 1, _texto(upd)))
            self._unir(fin, actualizacion)
            self._unir(actualizacion, c)
        else:
            self._unir(fin, c)
        self._revisar_infinito(nodo, cond, valor, c)
        return despues

    def _switch(self, nodo: Node, actual: Optional[Bloque]) -> Optional[Bloque]:
        cond = nodo.child_by_field_name("condition")
        c = self._condicion(actual, cond, f"switch {_texto(cond)}", nodo.start_point.row + 1)
        despues = self._nuevo()
        self.salidas_de_switch.append(despues)
        cuerpo = nodo.child_by_field_name("body")
        anterior: Optional[Bloque] = None
        hay_default = False
        for caso in (cuerpo.named_children if cuerpo is not None else []):
            if caso.type != "case_statement":
                continue
            valor = caso.child_by_field_name("value")
            hay_default = hay_default or valor is None
            b = self._nuevo()
            b.sentencias.append((caso.start_point.row + 1, f"case {_texto(valor)}:" if valor is not None else "default:"))
            self._unir(c, b, _texto(valor) if valor is not None else "default")
            self._unir(anterior, b)  # caída al caso siguiente sin break
            actual_caso: Optional[Bloque] = b
            for s in caso.named_children:
                if s is valor or s.type == "comment":
                    continue
                actual_caso = self.sentencia(s, actual_caso)
            anterior = actual_caso
        self._unir(anterior, despues)
        if not hay_default:
            self._unir(c, despues, "default")
        self.salidas_de_switch.pop()
        return despues

    def _revisar_infinito(self, nodo: Node, cond: Optional[Node], valor: Optional[bool], c: Bloque) -> None:
        cuerpo = nodo.child_by_field_name("body")
        if cuerpo is None or self._tiene_salida(cuerpo):
            return
        linea = nodo.start_point.row + 1
        if valor is True:
            self.infinitos.add(c.id)
            self.hallazgos.append(HallazgoCFG(
                "GIG002", "error", self.nombre, linea,
                f"El lazo de la línea {linea} no termina nunca: su condición es siempre verdadera y no tiene "
                "break, return, goto ni exit() que lo corte.",
                "Agregá la condición de corte (un break cuando se cumpla) o escribí la condición real del lazo."))
            return
        if cond is None or valor is False:
            return
        variables = self._variables_de(cond)
        if not variables:
            return
        modificadas = self._modificadas(cuerpo) | self._modificadas(nodo.child_by_field_name("update"))
        if variables & modificadas or variables & self.no_locales or variables & self.con_direccion:
            return
        self.infinitos.add(c.id)
        lista = ", ".join(sorted(variables))
        tapadas = sorted(variables & self._declaradas(cuerpo))
        sombra = (f" Ojo: el cuerpo declara otra variable {', '.join(tapadas)} que tapa a la de la condición; "
                  "la que se modifica adentro no es la que se evalúa.") if tapadas else ""
        self.hallazgos.append(HallazgoCFG(
            "GIG002", "advertencia", self.nombre, linea,
            f"La condición del lazo de la línea {linea} («{_texto(cond).strip('()')}») depende de {lista}, que el "
            f"cuerpo nunca modifica: o el lazo no se repite o no termina nunca.{sombra}",
            f"Revisá que el lazo avance: ¿falta actualizar {lista} (por ejemplo, un i++)?" if not tapadas
            else f"Asigná a la variable de afuera ({tapadas[0]} = …) en lugar de declarar otra."))

    @staticmethod
    def _tiene_salida(cuerpo: Node) -> bool:
        """break del propio lazo, return, goto o exit() en el cuerpo."""
        def recorrer(n: Node, profundidad_lazo: int, en_switch: bool) -> bool:
            if n.type in ("return_statement", "goto_statement"):
                return True
            if n.type == "break_statement" and profundidad_lazo == 0 and not en_switch:
                return True
            if n.type == "call_expression" and _texto(n.child_by_field_name("function")) in _TERMINAN:
                return True
            for h in n.children:
                es_lazo = h.type in ("while_statement", "for_statement", "do_statement")
                if recorrer(h, profundidad_lazo + es_lazo, en_switch or (h.type == "switch_statement" and profundidad_lazo == 0)):
                    return True
            return False
        return recorrer(cuerpo, 0, False)

    @staticmethod
    def _variables_de(cond: Node) -> Set[str]:
        """Los identificadores de la condición; vacío si llama a funciones o mira memoria (p->x, a[i], *p)."""
        nombres: Set[str] = set()
        for n in _recorrer(cond):
            if n.type in ("call_expression", "field_expression", "subscript_expression", "pointer_expression"):
                return set()
            if n.type == "identifier" and not n.is_missing and _texto(n):
                nombres.add(_texto(n))
        return nombres

    @staticmethod
    def _declaradas(nodo: Node) -> Set[str]:
        nombres: Set[str] = set()
        for n in _recorrer(nodo):
            if n.type == "declaration":
                for d in n.children_by_field_name("declarator"):
                    ident = d.child_by_field_name("declarator") if d.type == "init_declarator" else d
                    if ident is not None and ident.type == "identifier":
                        nombres.add(_texto(ident))
        return nombres

    @staticmethod
    def _modificadas(nodo: Optional[Node]) -> Set[str]:
        nombres: Set[str] = set()
        if nodo is None:
            return nombres
        for n in _recorrer(nodo):
            objetivo = None
            if n.type == "assignment_expression":
                objetivo = n.child_by_field_name("left")
            elif n.type == "update_expression":
                objetivo = n.child_by_field_name("argument")
            if objetivo is not None:
                nombres.update(_texto(x) for x in _recorrer(objetivo) if x.type == "identifier")
        return nombres

    def construir(self, funcion: Node) -> None:
        declarados = {_texto(n) for n in _recorrer(funcion) if n.type == "identifier"
                      and n.parent is not None and n.parent.type in ("init_declarator", "declaration",
                                                                      "parameter_declaration", "pointer_declarator",
                                                                      "array_declarator")}
        usados = {_texto(n) for n in _recorrer(funcion) if n.type == "identifier"}
        self.no_locales = usados - declarados
        self.con_direccion = {_texto(n.child_by_field_name("argument")) for n in _recorrer(funcion)
                              if n.type == "pointer_expression" and n.children and n.children[0].type == "&"}
        primero = self._nuevo()
        self._unir(self.entrada, primero)
        fin = self.sentencia(funcion.child_by_field_name("body"), primero)
        self._unir(fin, self.salida)


def _alcanzables(bloques: List[Bloque]) -> Set[int]:
    vistos = {0}
    pendientes = [0]
    while pendientes:
        for destino, _ in bloques[pendientes.pop()].sucesores:
            if destino not in vistos:
                vistos.add(destino)
                pendientes.append(destino)
    return vistos


def _nombre_funcion(funcion: Node) -> str:
    declarador = funcion.child_by_field_name("declarator")
    if declarador is None:
        return "?"
    for n in _recorrer(declarador):
        if n.type == "function_declarator":
            return _texto(n.child_by_field_name("declarator"))
    return "?"


def cfg_de_archivo(archivo: Path) -> List[CFGFuncion]:
    fuente = Path(archivo).read_text(encoding="utf-8", errors="replace")
    # tree-sitter reconoce los comentarios y los literales: no hace falta enmascararlos (y blanquear un
    # 'n' dejaba la condición incompleta).
    _ORIGINAL[0] = fuente.encode("utf-8")
    arbol = _parser().parse(_ORIGINAL[0])
    funciones: List[CFGFuncion] = []
    for nodo in _recorrer(arbol.root_node):
        if nodo.type != "function_definition":
            continue
        c = _Constructor(_nombre_funcion(nodo))
        c.construir(nodo)
        alcanzables = _alcanzables(c.bloques)
        hallazgos = list(c.hallazgos)
        for b in c.bloques:
            if b.id not in alcanzables and b.sentencias and b.tipo != "salida":
                desde, hasta = b.lineas
                cuales = f"La línea {desde}" if desde == hasta else f"Las líneas {desde}–{hasta}"
                verbo, pronombre = ("se ejecuta", "ella") if desde == hasta else ("se ejecutan", "ellas")
                hallazgos.append(HallazgoCFG(
                    "GIG001", "advertencia", c.nombre, desde,
                    f"{cuales} de {c.nombre}() no {verbo} nunca: no hay camino desde el inicio de la función "
                    f"hasta {pronombre}.",
                    "Borralas o revisá el return/break anterior (o la condición constante) que las deja afuera."))
        hallazgos.sort(key=lambda h: h.linea)
        funciones.append(CFGFuncion(c.nombre, nodo.start_point.row + 1, c.bloques, alcanzables, hallazgos, c.infinitos))
    return funciones


def _etiqueta(b: Bloque) -> str:
    if b.tipo == "entrada":
        return "inicio"
    if b.tipo == "salida":
        return "fin"
    desde, hasta = b.lineas
    rango = f"L{desde}" if desde == hasta else f"L{desde}–{hasta}"
    primera = b.sentencias[0][1] if b.sentencias else ""
    primera = primera if len(primera) <= 32 else primera[:31] + "…"
    resto = f" (+{len(b.sentencias) - 1})" if len(b.sentencias) > 1 else ""
    return f"{rango}: {primera}{resto}".replace('"', "'")


def mermaid(funciones: List[CFGFuncion]) -> str:
    lineas = ["flowchart TD"]
    for f in funciones:
        p = f"{f.nombre}_"
        # Los bloques vacíos de unión no se dibujan: sus aristas pasan de largo.
        visibles = {b.id for b in f.bloques if b.tipo in ("entrada", "salida", "condicion") or b.sentencias}

        def destino_visible(i: int, vistos: Optional[Set[int]] = None, f: CFGFuncion = f, visibles: Set[int] = visibles) -> List[int]:
            if i in visibles:
                return [i]
            vistos = vistos or set()
            if i in vistos:
                return []
            vistos.add(i)
            resultado: List[int] = []
            for d, _ in f.bloques[i].sucesores:
                resultado += destino_visible(d, vistos)
            return resultado

        lineas.append(f'  subgraph {p}fn ["{f.nombre}()"]')
        lineas.append("    direction TB")
        muertos, infinitos = [], []
        for b in f.bloques:
            if b.id not in visibles:
                continue
            forma = ('(["{}"])' if b.tipo in ("entrada", "salida") else '{{"{}"}}' if b.tipo == "condicion"
                     else '["{}"]').format(_etiqueta(b))
            lineas.append(f"    {p}{b.id}{forma}")
            if b.id not in f.alcanzables and b.tipo != "salida":
                muertos.append(f"{p}{b.id}")
            if b.id in f.bucles_infinitos:
                infinitos.append(f"{p}{b.id}")
        aristas = set()
        for b in f.bloques:
            if b.id not in visibles:
                continue
            for d, etiqueta in b.sucesores:
                for v in destino_visible(d):
                    aristas.add((b.id, v, etiqueta))
        for o, d, etiqueta in sorted(aristas):
            lineas.append(f"    {p}{o} -->{f'|{etiqueta}|' if etiqueta else ''} {p}{d}")
        lineas.append("  end")
        if muertos:
            lineas.append(f"  class {','.join(muertos)} muerto")
        if infinitos:
            lineas.append(f"  class {','.join(infinitos)} infinito")
    lineas.append("  classDef muerto fill:#fee2e2,stroke:#dc2626,stroke-dasharray: 4 4,color:#991b1b")
    lineas.append("  classDef infinito fill:#fef3c7,stroke:#d97706,stroke-width:2px")
    return "\n".join(lineas) + "\n"
