"""
Construccion del arbol sintactico a partir del postfix YA EXPANDIDO que
entrega shunting_yard.expandir_extensiones(), y su dibujo con matplotlib

"""

import os

import matplotlib
 # backend sin pantalla, solo para guardar PNG
matplotlib.use('Agg')         
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

from shunting_yard import CONCAT, EPSILON


class Nodo:
    """Nodo del arbol sintactico."""

    def __init__(self, tipo, valor=None, izq=None, der=None):
        # tipo: 'operando' | 'concat' | 'union' | 'estrella'
        self.tipo = tipo
        # texto del token, solo para 'operando'
        self.valor = valor        
        self.izq = izq
        self.der = der

    def etiqueta(self):
        if self.tipo == 'operando':
            return self.valor
        return {'concat': CONCAT, 'union': '|', 'estrella': '*'}[self.tipo]


def construir_arbol(postfix_expandido):
    """
    Construye el arbol de sintaxis a partir de una lista de tokens en
    postfix que ya no contiene + ni ? (solo |, · y *).
    """
    pila = []
    for token in postfix_expandido:
        if token == '*':
            a = pila.pop()
            pila.append(Nodo('estrella', izq=a))
        elif token == CONCAT:
            b = pila.pop(); a = pila.pop()
            pila.append(Nodo('concat', izq=a, der=b))
        elif token == '|':
            b = pila.pop(); a = pila.pop()
            pila.append(Nodo('union', izq=a, der=b))
        else:
            # operando: simbolo simple, clase de caracteres, char escapado o ε
            pila.append(Nodo('operando', valor=token))

    if len(pila) != 1:
        raise ValueError("postfix mal formado: la pila no quedo con un solo nodo")
    return pila.pop()


def recorrido_preorden(nodo):
    """Representacion textual del arbol (para inspeccion en consola)."""
    if nodo.tipo == 'operando':
        return nodo.valor
    if nodo.tipo == 'estrella':
        return f'({recorrido_preorden(nodo.izq)})*'
    op = nodo.etiqueta()
    return f'({recorrido_preorden(nodo.izq)}{op}{recorrido_preorden(nodo.der)})'


# Dibujo del arbol con matplotlib (circulo = operando, rectangulo = operador)

def _ancho_etiqueta(etiqueta):
    """Ancho visual necesario para una etiqueta (radio del circulo u operador)."""
    return max(0.6, 0.11 * len(etiqueta) + 0.2) * 2 + 0.3


def _calcular_posiciones(nodo, profundidad, siguiente_x, posiciones):
    """
    Recorrido postorden que asigna:
      - a cada hoja una coordenada x consecutiva, reservando un ancho
        proporcional al tamano de su etiqueta (para que hojas con texto
        largo, como una clase de caracteres [ae03], no se encimen)
      - a cada nodo interno la x promedio de sus hijos
      - a todos los nodos y = -profundidad (la raiz queda arriba, en y=0)

    siguiente_x es una lista de un elemento usada como contador mutable
    (equivalente a una variable "nonlocal" pasada por referencia).
    Devuelve la coordenada x asignada al nodo.
    """
    hijos = [h for h in (nodo.izq, nodo.der) if h is not None]

    if not hijos:
        ancho = _ancho_etiqueta(nodo.etiqueta())
        x = siguiente_x[0] + ancho / 2
        siguiente_x[0] += ancho
    else:
        xs_hijos = [_calcular_posiciones(h, profundidad + 1, siguiente_x, posiciones)
                    for h in hijos]
        x = sum(xs_hijos) / len(xs_hijos)

    posiciones[id(nodo)] = (x, -profundidad)
    return x


def _dibujar_nodo(ax, nodo, posiciones):
    x, y = posiciones[id(nodo)]
    etiqueta = nodo.etiqueta()
    radio = max(0.6, 0.11 * len(etiqueta) + 0.2)

    if nodo.tipo == 'operando':
        ax.add_patch(Circle((x, y), radio, facecolor='white',
                             edgecolor='black', zorder=2))
    else:
        ax.add_patch(Rectangle((x - radio, y - 0.3), 2 * radio, 0.6,
                                facecolor='white', edgecolor='black', zorder=2))
    ax.text(x, y, etiqueta, ha='center', va='center', fontsize=11, zorder=3)


def _dibujar_arista(ax, padre, hijo, posiciones):
    x1, y1 = posiciones[id(padre)]
    x2, y2 = posiciones[id(hijo)]
    ax.plot([x1, x2], [y1 - 0.3, y2 + 0.3], color='black', linewidth=1, zorder=1)


def _recorrer_dibujo(ax, nodo, posiciones):
    _dibujar_nodo(ax, nodo, posiciones)
    for hijo in (nodo.izq, nodo.der):
        if hijo is not None:
            _dibujar_arista(ax, nodo, hijo, posiciones)
            _recorrer_dibujo(ax, hijo, posiciones)


def dibujar_arbol(raiz, nombre, carpeta='salida'):
    """Genera un PNG del arbol con matplotlib y devuelve la ruta del archivo."""
    posiciones = {}
    _calcular_posiciones(raiz, profundidad=0, siguiente_x=[0], posiciones=posiciones)

    xs = [p[0] for p in posiciones.values()]
    ys = [p[1] for p in posiciones.values()]
    ancho = max(4.0, (max(xs) - min(xs)) * 1.2 + 2)
    alto = max(3.0, (max(ys, default=0) - min(ys)) * 1.2 + 2)

    fig, ax = plt.subplots(figsize=(ancho, alto))
    _recorrer_dibujo(ax, raiz, posiciones)

    ax.set_xlim(min(xs) - 1, max(xs) + 1)
    ax.set_ylim(min(ys) - 1, max(ys, default=0) + 1)
    ax.axis('off')
    ax.set_aspect('equal')

    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, f'{nombre}.png')
    fig.savefig(ruta, bbox_inches='tight', dpi=150)
    plt.close(fig)
    return ruta
