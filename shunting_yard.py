import sys

CONCAT = "\u00b7"
"""
Simbolo interno para la concatenacion explicita (punto medio).

Se usa este simbolo y no el punto normal porque el punto normal aparece como
caracter literal dentro de las expresiones del Problema 1 (por ejemplo en
"[ae03]+@[ae03]+.(com|net|org)"). Si se usara el mismo caracter para las dos
cosas seria imposible distinguir el operador del literal. Basta cambiar esta
constante para usar otro simbolo.
"""
EPSILON = "\u03b5"

PRECEDENCIA = {
    "*": 4,
    "+": 4,
    "?": 4,
    CONCAT: 3,
    "|": 2,
}
"""
Tabla de precedencias. A mayor numero, mayor prioridad.

    4 -> * + ?   cerradura de Kleene, positiva y opcional (unarios postfijos)
    3 -> CONCAT  concatenacion (operador implicito que se inserta)
    2 -> |       union o alternancia (la mas debil)

Los parentesis no llevan precedencia: se manejan como marcas de agrupacion.
"""

UNARIOS = {"*", "+", "?"}
BINARIOS = {CONCAT, "|"}
ESCAPE = "\\"


# SECCION 1. Estructura de datos: la pila

class Pila:

    def __init__(self):
        self._items = []

    def push(self, item):
        self._items.append(item)

    def pop(self):
        if self.esta_vacia():
            raise IndexError("pop sobre una pila vacia")
        return self._items.pop()

    def peek(self):
        """Consulta el tope sin retirarlo. Devuelve None si la pila esta vacia."""
        if self.esta_vacia():
            return None
        return self._items[-1]

    def esta_vacia(self):
        return len(self._items) == 0

    def tamano(self):
        return len(self._items)

    def como_texto(self):
        """Vista de la pila con la base a la izquierda y el tope a la derecha."""
        if self.esta_vacia():
            return "(vacia)"
        return " ".join(self._items)



# SECCION 2. Analizador lexico (tokenizer)



class Token:
    """
    Unidad minima de la expresion.

    tipo puede ser:
        LITERAL  -> operando: un simbolo, una clase de caracteres o un
                    caracter escapado
        OP       -> operador: * + ? | o la concatenacion
        ABRE     -> parentesis de apertura
        CIERRA   -> parentesis de cierre

    texto es lo que se muestra en pantalla, valor es el contenido util.
    """

    def __init__(self, tipo, texto, valor=None):
        self.tipo = tipo
        self.texto = texto
        self.valor = valor if valor is not None else texto

    def es_operando(self):
        return self.tipo == "LITERAL"

    def __repr__(self):
        return self.texto


def tokenizar(expresion):
    """
    Convierte la cadena de entrada en una lista de Tokens.

    Reglas aplicadas, en orden de prioridad:

      1. Barra invertida: el caracter siguiente se toma como LITERAL sin
         importar si normalmente seria un operador. Este es el verificador
         de caracteres escapados que pide el enunciado.
      2. Corchete de apertura: se consume hasta el corchete de cierre y toda
         la clase de caracteres se guarda como UN SOLO operando, de modo que
         un operador posterior aplique a la clase completa.
      3. Los simbolos * + ? | se marcan como operadores.
      4. Los parentesis sin escapar se marcan como agrupacion.
      5. Los espacios se descartan.
      6. Cualquier otro caracter, incluido el punto, es un operando literal.

    Devuelve (tokens, error). Si error no es None la expresion es invalida.
    """
    tokens = []
    i = 0
    n = len(expresion)

    while i < n:
        c = expresion[i]

        if c == ESCAPE:
            if i + 1 >= n:
                return None, "la expresion termina con una barra invertida sin caracter que escapar"
            siguiente = expresion[i + 1]
            tokens.append(Token("LITERAL", ESCAPE + siguiente, siguiente))
            i += 2
            continue

        if c == "[":
            cierre = _buscar_cierre_de_clase(expresion, i)
            if cierre is None:
                return None, "clase de caracteres abierta en la posicion {0} sin su corchete de cierre".format(i)
            texto = expresion[i:cierre + 1]
            tokens.append(Token("LITERAL", texto, texto))
            i = cierre + 1
            continue

        if c in UNARIOS or c == "|":
            tokens.append(Token("OP", c, c))
            i += 1
            continue

        if c == "(":
            tokens.append(Token("ABRE", "(", "("))
            i += 1
            continue

        if c == ")":
            tokens.append(Token("CIERRA", ")", ")"))
            i += 1
            continue

        if c.isspace():
            i += 1
            continue

        tokens.append(Token("LITERAL", c, c))
        i += 1

    return tokens, None


def _buscar_cierre_de_clase(expresion, inicio):
    """Devuelve el indice del corchete que cierra la clase, o None si no existe."""
    j = inicio + 1
    while j < len(expresion):
        if expresion[j] == ESCAPE:
            j += 2
            continue
        if expresion[j] == "]":
            return j
        j += 1
    return None




# SECCION 4. Insercion de la concatenacion explicita



def insertar_concatenacion(tokens):
    """
    En una expresion regular la concatenacion no se escribe: "ab" significa
    "a concatenado con b". Shunting Yard necesita ver todos los operadores,
    asi que aqui se hace explicito ese operador invisible.

    Se inserta CONCAT entre un token izquierdo y uno derecho cuando:

        izquierdo termina un operando  -> LITERAL, parentesis de cierre,
                                          o un unario postfijo (* + ?)
        derecho empieza un operando    -> LITERAL o parentesis de apertura

    Ejemplos:
        a b        -> a CONCAT b
        ) (        -> ) CONCAT (
        * a        -> * CONCAT a
        | a        -> no se inserta, la union ya es un operador binario
    """
    if not tokens:
        return []

    resultado = [tokens[0]]

    for actual in tokens[1:]:
        anterior = resultado[-1]

        cierra_operando = (
            anterior.tipo == "LITERAL"
            or anterior.tipo == "CIERRA"
            or (anterior.tipo == "OP" and anterior.valor in UNARIOS)
        )
        abre_operando = actual.tipo == "LITERAL" or actual.tipo == "ABRE"

        if cierra_operando and abre_operando:
            resultado.append(Token("OP", CONCAT, CONCAT))

        resultado.append(actual)

    return resultado



# SECCION 5. Algoritmo de Shunting Yard



def shunting_yard(tokens):
    """
    Convierte una lista de tokens en notacion infix a notacion postfix.

    Reglas, aplicadas token por token:

      OPERANDO   -> va directo a la salida, sin pasar por la pila.
      OPERADOR   -> mientras el tope de la pila sea un operador con
                    precedencia mayor o igual a la del operador actual,
                    se hace pop de ese tope hacia la salida.
                    Terminado el ciclo, se hace push del operador actual.
      ABRE       -> push, actua como barrera: nada se saca mas alla de el.
      CIERRA     -> pop hacia la salida hasta encontrar el parentesis de
                    apertura, que se descarta junto con el de cierre.
      FINAL      -> se vacia la pila hacia la salida.

    Devuelve (salida, pasos, error).
    """
    salida = []
    pila = Pila()
    pasos = []

    for token in tokens:

        if token.es_operando():
            salida.append(token.texto)
            _registrar(pasos, token, "operando a la salida", pila, salida)
            continue

        if token.tipo == "ABRE":
            pila.push(token.texto)
            _registrar(pasos, token, "push (", pila, salida)
            continue

        if token.tipo == "CIERRA":
            encontrado = False
            while not pila.esta_vacia():
                tope = pila.pop()
                if tope == "(":
                    encontrado = True
                    break
                salida.append(tope)
                _registrar(pasos, token, "pop " + tope + " a la salida", pila, salida)
            if not encontrado:
                _registrar(pasos, token, "ERROR: cierre sin apertura", pila, salida)
                return None, pasos, "parentesis de cierre sin su apertura correspondiente"
            _registrar(pasos, token, "descarta el par ( )", pila, salida)
            continue

        actual = token.valor
        prioridad_actual = PRECEDENCIA[actual]

        while (not pila.esta_vacia()
               and pila.peek() != "("
               and PRECEDENCIA[pila.peek()] >= prioridad_actual):
            tope = pila.pop()
            salida.append(tope)
            _registrar(
                pasos, token,
                "pop " + tope + " por precedencia",
                pila, salida)

        pila.push(actual)
        _registrar(pasos, token, "push " + actual, pila, salida)

    while not pila.esta_vacia():
        tope = pila.pop()
        if tope == "(":
            _registrar(pasos, Token("FIN", "fin"), "ERROR: apertura sin cierre", pila, salida)
            return None, pasos, "quedo un parentesis de apertura sin cerrar"
        salida.append(tope)
        _registrar(pasos, Token("FIN", "fin"), "fin: pop " + tope, pila, salida)

    return salida, pasos, None


def _registrar(pasos, token, accion, pila, salida):
    """Guarda la foto del estado despues de ejecutar una accion."""
    pasos.append({
        "token": token.texto,
        "accion": accion,
        "pila": pila.como_texto(),
        "salida": " ".join(salida) if salida else "(vacia)",
    })



 # SECCION 6. Expansion de las extensiones + y ?


def expandir_extensiones(postfix):
    """
    Convierte las extensiones a las tres operaciones basicas de una expresion
    regular: union, concatenacion y cerradura de Kleene.

    Identidades utilizadas:

        A+  equivale a  A A*      un A obligatorio seguido de cero o mas
        A?  equivale a  A | eps   el propio A o la cadena vacia

    La expansion se hace sobre la forma postfix porque ahi cada operando ya
    es una subexpresion completa: basta con una pila de fragmentos.

        operando  -> se apila como fragmento de un solo elemento
        unario    -> se saca un fragmento y se devuelve transformado
        binario   -> se sacan dos fragmentos y se combinan

    Devuelve (postfix_expandido, cambios) donde cambios es la lista de
    reescrituras aplicadas.
    """
    fragmentos = Pila()
    cambios = []

    for simbolo in postfix:

        if simbolo == "*":
            a = fragmentos.pop()
            fragmentos.push(a + ["*"])
            continue

        if simbolo == "+":
            a = fragmentos.pop()
            texto = " ".join(a)
            fragmentos.push(a + a + ["*"] + [CONCAT])
            cambios.append("( " + texto + " )+  se reescribe como  ( " + texto + " )( " + texto + " )*")
            continue

        if simbolo == "?":
            a = fragmentos.pop()
            texto = " ".join(a)
            fragmentos.push(a + [EPSILON] + ["|"])
            cambios.append("( " + texto + " )?  se reescribe como  ( " + texto + " ) | " + EPSILON)
            continue

        if simbolo in BINARIOS:
            b = fragmentos.pop()
            a = fragmentos.pop()
            fragmentos.push(a + b + [simbolo])
            continue

        fragmentos.push([simbolo])

    if fragmentos.tamano() != 1:
        return None, cambios

    return fragmentos.pop(), cambios



# SECCION 7. Impresion de resultados


LINEA_GRUESA = "-" * 100


def imprimir_tabla_precedencias():
    print(LINEA_GRUESA)
    print(" TABLA DE PRECEDENCIAS")
    print(LINEA_GRUESA)
    print("   4  |  " + "* + ?" + "   cerradura de Kleene, positiva y opcional (unarios postfijos)")
    print("   3  |  " + CONCAT + "       concatenacion implicita, insertada por el programa")
    print("   2  |  " + "|" + "       union o alternancia")
    print("      |  ( )     agrupacion, sin precedencia: actuan como barrera en la pila")
    print(LINEA_GRUESA)
    print()


def imprimir_resultado(numero, original, tokens_con_concat, postfix, pasos,
                       error, expandida, cambios):
    print(LINEA_GRUESA)
    print(" EXPRESION {0}:  {1}".format(numero, original))
    print(LINEA_GRUESA)

    if tokens_con_concat is not None:
        print("  Con concatenacion explicita:")
        print("      " + " ".join(t.texto for t in tokens_con_concat))
        print()

    if pasos:
        ancho_token = max(5, max(len(p["token"]) for p in pasos))
        ancho_accion = max(6, max(len(p["accion"]) for p in pasos))
        ancho_pila = max(4, max(len(p["pila"]) for p in pasos))

        print("  Pasos de la conversion:")
        print("     No.  | {0:<{4}} | {1:<{5}} | {2:<{6}} | Salida".format(
            "Token", "Accion", "Pila", 0, ancho_token, ancho_accion, ancho_pila))
        print("    " + "-" * 6 + "|" + "-" * (ancho_token + 2) + "|"
              + "-" * (ancho_accion + 2) + "|" + "-" * (ancho_pila + 2) + "|" + "-" * 12)
        for i, p in enumerate(pasos, start=1):
            print("    {0:>4}  | {1:<{5}} | {2:<{6}} | {3:<{7}} | {4}".format(
                i, p["token"], p["accion"], p["pila"], p["salida"],
                ancho_token, ancho_accion, ancho_pila))
        print()

    if error is not None:
        print("  RESULTADO: expresion invalida")
        print("  Detalle:   " + error)
        print()
        return

    print("  Salida en formato postfix:")
    print("      " + " ".join(postfix))
    print()

    if cambios:
        print("  Extensiones convertidas a operaciones basicas:")
        for c in cambios:
            print("      " + c)
        print()

    if expandida is not None:
        print("  Postfix sin extensiones (solo union, concatenacion y Kleene):")
        print("      " + " ".join(expandida))
        print()



# SECCION 8. Programa principal



def procesar_linea(numero, expresion):
    """Ejecuta la cadena completa de pasos sobre una sola expresion."""
    tokens, error = tokenizar(expresion)
    if error is not None:
        imprimir_resultado(numero, expresion, None, None, [], error, None, [])
        return False

    tokens = insertar_concatenacion(tokens)
    postfix, pasos, error = shunting_yard(tokens)

    if error is not None:
        imprimir_resultado(numero, expresion, tokens, None, pasos, error, None, [])
        return False

    expandida, cambios = expandir_extensiones(postfix)
    imprimir_resultado(numero, expresion, tokens, postfix, pasos, None,
                       expandida, cambios)
    return True


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 shunting_yard.py <archivo.txt>")
        sys.exit(1)

    ruta = sys.argv[1]

    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            lineas = archivo.readlines()
    except FileNotFoundError:
        print("ERROR: no se encontro el archivo " + ruta)
        sys.exit(1)

    print()
    print(LINEA_GRUESA)
    print(" ALGORITMO DE SHUNTING YARD  -  archivo procesado: " + ruta)
    print(LINEA_GRUESA)
    print()

    imprimir_tabla_precedencias()

    total = 0
    correctas = 0

    for numero, linea in enumerate(lineas, start=1):
        expresion = linea.rstrip("\n").rstrip("\r")

        if expresion.strip() == "" or expresion.lstrip().startswith("//"):
            continue

        total += 1
        if procesar_linea(numero, expresion):
            correctas += 1

    print(LINEA_GRUESA)
    print(" RESUMEN: {0} de {1} expresiones convertidas correctamente".format(
        correctas, total))
    print(LINEA_GRUESA)
    print()


if __name__ == "__main__":
    main()
