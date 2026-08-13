"""
Construccion del AFN por el algoritmo de Thompson a partir del arbol
sintactico que entrega arbol_sintactico.construir_arbol(), su dibujo con
matplotlib y su simulacion directa sobre la cadena w.


Cada llamada recursiva devuelve un Fragmento: un pedazo de AFN con
exactamente un estado de entrada y un estado de salida. Esa es la
propiedad que hace que las reglas se puedan componer entre si.
"""

import os

import matplotlib
# backend sin pantalla, solo para guardar PNG
matplotlib.use('Agg')         
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch

from shunting_yard import EPSILON


# SECCION 1. Fragmento: un pedazo de AFN con una entrada y una salida


class Fragmento:
    """
    Pedazo de automata con un unico estado de entrada y uno de salida.

    Ademas de los estados guarda la geometria del dibujo (posicion de cada
    estado, ancho total y extension vertical). Las coordenadas se calculan
    al mismo tiempo que se construye el automata: cada regla de Thompson
    sabe donde acomodar los fragmentos que recibe, y asi el dibujo final
    refleja la estructura del arbol en lugar de quedar amontonado.
    """

    def __init__(self, inicio, fin, posiciones, ancho, y_min, y_max):
        self.inicio = inicio
        self.fin = fin
        self.posiciones = posiciones      # estado -> (x, y)
        self.ancho = ancho
        self.y_min = y_min
        self.y_max = y_max

    def desplazar(self, dx, dy):
        """Mueve todo el fragmento sin alterar su estructura."""
        for estado, (x, y) in self.posiciones.items():
            self.posiciones[estado] = (x + dx, y + dy)
        self.y_min += dy
        self.y_max += dy


# SECCION 2. El automata finito no determinista


class AFN:
    """
    AFN de Thompson.

    transiciones: estado -> lista de (etiqueta, destino)
                  la etiqueta EPSILON representa una transicion vacia
    """

    def __init__(self, transiciones, inicial, aceptacion, posiciones,
                 curvaturas=None, expresion=''):
        self.transiciones = transiciones
        self.inicial = inicial
        self.aceptacion = aceptacion
        self.posiciones = posiciones
        # (origen, destino) -> curvatura del arco al dibujar; 0 es recta
        self.curvaturas = curvaturas if curvaturas is not None else {}
        self.expresion = expresion

    def estados(self):
        return sorted(self.transiciones.keys())

    def alfabeto(self):
        """Simbolos reales del automata, sin contar epsilon."""
        simbolos = set()
        for salidas in self.transiciones.values():
            for etiqueta, _ in salidas:
                if etiqueta != EPSILON:
                    simbolos.add(etiqueta)
        return sorted(simbolos)

    # SECCION 2.1. Simulacion del AFN

    def cerradura_epsilon(self, conjunto):
        """
        Todos los estados alcanzables desde el conjunto usando solo
        transiciones epsilon. Se usa una pila y un conjunto de visitados:
        sin los visitados la cerradura de una estrella daria vueltas para
        siempre, porque la estrella crea un ciclo de epsilons.
        """
        alcanzados = set(conjunto)
        pila = list(conjunto)

        while pila:
            estado = pila.pop()
            for etiqueta, destino in self.transiciones[estado]:
                if etiqueta == EPSILON and destino not in alcanzados:
                    alcanzados.add(destino)
                    pila.append(destino)

        return alcanzados

    def mover(self, conjunto, caracter):
        """Estados alcanzables desde el conjunto consumiendo un caracter."""
        destinos = set()
        for estado in conjunto:
            for etiqueta, destino in self.transiciones[estado]:
                if etiqueta != EPSILON and coincide(etiqueta, caracter):
                    destinos.add(destino)
        return destinos

    def simular(self, w):
        """
        Simula el AFN directamente, sin convertirlo a AFD.

        Se mantiene el conjunto de todos los estados en los que el
        automata podria estar a la vez. Se acepta si al terminar la cadena
        el estado de aceptacion esta en ese conjunto.

        Devuelve (aceptada, traza) donde traza son las fotos del conjunto
        de estados paso a paso.
        """
        actual = self.cerradura_epsilon({self.inicial})
        traza = [('inicio', sorted(actual))]

        for caracter in w:
            movidos = self.mover(actual, caracter)
            actual = self.cerradura_epsilon(movidos)
            traza.append((caracter, sorted(actual)))
            if not actual:
                break

        return self.aceptacion in actual, traza

    def tabla_transiciones(self):
        """Lista de filas (estado, etiqueta, destinos) para imprimir."""
        filas = []
        for estado in self.estados():
            agrupado = {}
            for etiqueta, destino in self.transiciones[estado]:
                agrupado.setdefault(etiqueta, []).append(destino)
            for etiqueta in sorted(agrupado, key=lambda e: (e == EPSILON, e)):
                filas.append((estado, etiqueta, sorted(agrupado[etiqueta])))
        return filas


def coincide(etiqueta, caracter):
    """
    Decide si una etiqueta de transicion acepta el caracter leido.

    La etiqueta puede ser:
        un simbolo normal    a      acepta solo 'a'
        un caracter escapado        acepta el caracter escapado, no el operador
        una clase [ae03]            acepta cualquiera de los caracteres listados
                                    (tambien admite rangos como [a-z])
    """
    if len(etiqueta) == 2 and etiqueta[0] == '\\':
        return caracter == etiqueta[1]

    if len(etiqueta) >= 2 and etiqueta[0] == '[' and etiqueta[-1] == ']':
        return _en_clase(etiqueta[1:-1], caracter)

    return caracter == etiqueta


def _en_clase(contenido, caracter):
    """Evalua la pertenencia a una clase de caracteres, con rangos a-z."""
    i = 0
    while i < len(contenido):
        if i + 2 < len(contenido) and contenido[i + 1] == '-':
            if contenido[i] <= caracter <= contenido[i + 2]:
                return True
            i += 3
            continue
        if contenido[i] == caracter:
            return True
        i += 1
    return False


# SECCION 3. Las cuatro reglas de Thompson


# Separacion horizontal reservada para las transiciones epsilon que
# agregan la concatenacion, la union y la estrella.
_HUECO = 1.6
# Separacion vertical entre las dos ramas de una union.
_SEPARACION = 1.1


class _Constructor:
    """Lleva el contador de estados y la tabla de transiciones en comun."""

    def __init__(self):
        self.contador = 0
        self.transiciones = {}
        self.curvaturas = {}

    def nuevo_estado(self):
        estado = self.contador
        self.contador += 1
        self.transiciones[estado] = []
        return estado

    def conectar(self, origen, etiqueta, destino):
        self.transiciones[origen].append((etiqueta, destino))

    def curvar(self, origen, destino, altura, distancia):
        """
        Marca una transicion para dibujarse como arco en lugar de recta.

        Las dos transiciones largas de la estrella (el salto y el regreso)
        unen estados que tienen otros estados en medio; si se dibujaran
        rectas pasarian por encima de ellos. Aqui se calcula la curvatura
        necesaria para que el arco salga por fuera del fragmento: para un
        arco de matplotlib la separacion maxima respecto de la cuerda es
        rad * distancia / 2, asi que rad = 2 * altura / distancia.
        """
        self.curvaturas[(origen, destino)] = 2.0 * altura / distancia

    # Regla 1: hoja. Dos estados nuevos unidos por el simbolo.
    #
    #     (i) --a--> (f)
    #
    def basico(self, etiqueta):
        i = self.nuevo_estado()
        f = self.nuevo_estado()
        self.conectar(i, etiqueta, f)
        return Fragmento(i, f, {i: (0.0, 0.0), f: (_HUECO, 0.0)},
                         ancho=_HUECO, y_min=0.0, y_max=0.0)

    # Regla 2: concatenacion A B. El final de A se une al inicio de B con
    # una transicion epsilon. No se crean estados nuevos.
    #
    #     (iA) ~~A~~> (fA) --e--> (iB) ~~B~~> (fB)
    #
    def concatenar(self, a, b):
        b.desplazar(a.ancho + _HUECO, 0)
        self.conectar(a.fin, EPSILON, b.inicio)

        posiciones = dict(a.posiciones)
        posiciones.update(b.posiciones)
        return Fragmento(a.inicio, b.fin, posiciones,
                         ancho=a.ancho + _HUECO + b.ancho,
                         y_min=min(a.y_min, b.y_min),
                         y_max=max(a.y_max, b.y_max))

# Regla 3: union A|B. Un inicio nuevo con epsilon hacia los dos

    def unir(self, a, b):
        a.desplazar(_HUECO, _SEPARACION - a.y_min)
        b.desplazar(_HUECO, -_SEPARACION - b.y_max)

        ancho = _HUECO + max(a.ancho, b.ancho) + _HUECO
        i = self.nuevo_estado()
        f = self.nuevo_estado()

        self.conectar(i, EPSILON, a.inicio)
        self.conectar(i, EPSILON, b.inicio)
        self.conectar(a.fin, EPSILON, f)
        self.conectar(b.fin, EPSILON, f)

        posiciones = dict(a.posiciones)
        posiciones.update(b.posiciones)
        posiciones[i] = (0.0, 0.0)
        posiciones[f] = (ancho, 0.0)

        return Fragmento(i, f, posiciones, ancho=ancho,
                         y_min=min(a.y_min, b.y_min),
                         y_max=max(a.y_max, b.y_max))

    # Regla 4: cerradura de Kleene A*. Inicio y final nuevos, con el
    # camino de salto (cero repeticiones) y el de regreso (una mas).
    #
    #                 .--------e--------.
    #                 v                 |
    #     (i) --e--> (iA) ~~A~~> (fA) --e--> (f)
    #      |                                  ^
    #      '---------------e------------------'
    #
    def estrella(self, a):
        a.desplazar(_HUECO, 0)

        ancho = _HUECO + a.ancho + _HUECO
        i = self.nuevo_estado()
        f = self.nuevo_estado()

        self.conectar(i, EPSILON, a.inicio)
        self.conectar(i, EPSILON, f)
        self.conectar(a.fin, EPSILON, a.inicio)
        self.conectar(a.fin, EPSILON, f)

        # El regreso sale por arriba del fragmento y el salto por abajo.
        self.curvar(a.fin, a.inicio, a.y_max + 0.9, a.ancho)
        self.curvar(i, f, -a.y_min + 0.9, ancho)

        posiciones = dict(a.posiciones)
        posiciones[i] = (0.0, 0.0)
        posiciones[f] = (ancho, 0.0)

        return Fragmento(i, f, posiciones, ancho=ancho,
                         y_min=a.y_min - _SEPARACION,
                         y_max=a.y_max + _SEPARACION)


def _construir(nodo, constructor):
    """Recorrido postorden del arbol: primero los hijos, luego el nodo."""
    if nodo.tipo == 'operando':
        return constructor.basico(nodo.valor)

    if nodo.tipo == 'estrella':
        return constructor.estrella(_construir(nodo.izq, constructor))

    izquierdo = _construir(nodo.izq, constructor)
    derecho = _construir(nodo.der, constructor)

    if nodo.tipo == 'concat':
        return constructor.concatenar(izquierdo, derecho)
    if nodo.tipo == 'union':
        return constructor.unir(izquierdo, derecho)

    raise ValueError('tipo de nodo desconocido: ' + str(nodo.tipo))


def thompson(raiz, expresion=''):
    """Aplica el algoritmo de Thompson al arbol y devuelve el AFN."""
    constructor = _Constructor()
    fragmento = _construir(raiz, constructor)
    return AFN(constructor.transiciones, fragmento.inicio, fragmento.fin,
               fragmento.posiciones, constructor.curvaturas, expresion)


# SECCION 4. Dibujo del AFN con matplotlib


_RADIO = 0.32


def _flecha(ax, p1, p2, etiqueta, curvatura):
    """
    Dibuja una transicion recortada en el borde de los dos circulos y
    devuelve la posicion del punto mas alejado del arco, para que quien
    dibuja pueda ajustar los margenes de la figura.

    Un arco de matplotlib con rad positivo se abomba hacia la derecha de
    la direccion del recorrido, asi que en una arista que va hacia la
    derecha el arco sale por abajo y en una que regresa sale por arriba.
    """
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    distancia = (dx * dx + dy * dy) ** 0.5 or 1.0
    ux, uy = dx / distancia, dy / distancia

    inicio = (x1 + ux * _RADIO, y1 + uy * _RADIO)
    final = (x2 - ux * _RADIO, y2 - uy * _RADIO)

    ax.add_patch(FancyArrowPatch(
        inicio, final,
        connectionstyle='arc3,rad={0}'.format(curvatura),
        arrowstyle='-|>', mutation_scale=11,
        linewidth=1.0, color='black', shrinkA=0, shrinkB=0, zorder=1))

    # Vector perpendicular hacia la derecha del recorrido: hacia alli se
    # abomba el arco cuando la curvatura es positiva.
    dx_perp, dy_perp = uy, -ux

    # El arco real va de borde a borde de los circulos, no de centro a
    # centro, asi que su altura se calcula sobre esa cuerda recortada.
    cuerda = distancia - 2 * _RADIO
    altura = curvatura * cuerda / 2

    # Punto medio del arco, y la etiqueta un poco mas afuera todavia.
    mx = (inicio[0] + final[0]) / 2 + dx_perp * altura
    my = (inicio[1] + final[1]) / 2 + dy_perp * altura

    if curvatura == 0:
        # En una recta la etiqueta va al lado izquierdo del recorrido.
        fuera_x, fuera_y = -dx_perp, -dy_perp
    elif curvatura > 0:
        fuera_x, fuera_y = dx_perp, dy_perp
    else:
        fuera_x, fuera_y = -dx_perp, -dy_perp

    ax.text(mx + fuera_x * 0.26, my + fuera_y * 0.26, etiqueta,
            ha='center', va='center', fontsize=9, color='black', zorder=4,
            bbox=dict(boxstyle='round,pad=0.12', facecolor='white',
                      edgecolor='none'))

    return (mx, my)


def _alcance_vertical(afn):
    """Extension vertical del dibujo contando los arcos, no solo los estados."""
    ys = [p[1] for p in afn.posiciones.values()]
    minimo, maximo = min(ys), max(ys)

    for (origen, destino), curvatura in afn.curvaturas.items():
        x1, y1 = afn.posiciones[origen]
        x2, y2 = afn.posiciones[destino]
        distancia = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5 or 1.0
        ux = (x2 - x1) / distancia
        apice = (y1 + y2) / 2 + (-ux) * curvatura * (distancia - 2 * _RADIO) / 2
        minimo = min(minimo, apice)
        maximo = max(maximo, apice)

    return minimo, maximo


def dibujar_afn(afn, nombre, carpeta='salida'):
    """Genera un PNG del AFN y devuelve la ruta del archivo."""
    posiciones = afn.posiciones
    xs = [p[0] for p in posiciones.values()]
    ys = [p[1] for p in posiciones.values()]

    escala = 0.75
    alcance_y = _alcance_vertical(afn)
    ancho = max(5.0, (max(xs) - min(xs) + 4) * escala)
    alto = max(3.0, (alcance_y[1] - alcance_y[0] + 3) * escala)

    fig, ax = plt.subplots(figsize=(ancho, alto))

    # Transiciones. Las que la estrella marco como arcos salen por fuera
    # del fragmento; el resto van rectas.
    extremos_y = list(ys)
    for origen in afn.estados():
        for etiqueta, destino in afn.transiciones[origen]:
            x1, y1 = posiciones[origen]
            x2, y2 = posiciones[destino]
            curvatura = afn.curvaturas.get((origen, destino), 0.0)
            _, apice_y = _flecha(ax, (x1, y1), (x2, y2), etiqueta, curvatura)
            extremos_y.append(apice_y)

    # Estados
    for estado in afn.estados():
        x, y = posiciones[estado]
        ax.add_patch(Circle((x, y), _RADIO, facecolor='white',
                            edgecolor='black', linewidth=1.2, zorder=2))
        if estado == afn.aceptacion:
            ax.add_patch(Circle((x, y), _RADIO * 0.76, facecolor='none',
                                edgecolor='black', linewidth=1.0, zorder=3))
        ax.text(x, y, str(estado), ha='center', va='center',
                fontsize=9, zorder=4)

    # Marca del estado inicial
    xi, yi = posiciones[afn.inicial]
    ax.add_patch(FancyArrowPatch((xi - 1.1, yi), (xi - _RADIO, yi),
                                 arrowstyle='-|>', mutation_scale=12,
                                 linewidth=1.2, color='black',
                                 shrinkA=0, shrinkB=0, zorder=1))
    ax.text(xi - 1.25, yi, 'inicio', ha='right', va='center', fontsize=9)

    titulo = 'AFN de Thompson'
    if afn.expresion:
        titulo += '     r = ' + afn.expresion
    ax.set_title(titulo, fontsize=11)

    ax.set_xlim(min(xs) - 2.6, max(xs) + 1.2)
    ax.set_ylim(min(extremos_y) - 1.0, max(extremos_y) + 1.0)
    ax.axis('off')
    ax.set_aspect('equal')

    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, nombre + '.png')
    fig.savefig(ruta, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return ruta
