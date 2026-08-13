"""
Laboratorio 4 - Problema 1
Construccion del AFN por el algoritmo de Thompson y simulacion del AFN.

Flujo completo por cada linea del archivo de entrada:

    expresion regular r
        -> tokenizar                      (shunting_yard, Lab 2)
        -> insertar concatenacion         (shunting_yard, Lab 2)
        -> shunting yard: infix a postfix (shunting_yard, Lab 2)
        -> expandir + y ?                 (A+ = A A*  ,  A? = A|e)
        -> construir el arbol sintactico  (arbol_sintactico, Lab 3)
        -> dibujar el arbol
        -> algoritmo de Thompson          (thompson, Lab 4)
        -> dibujar el AFN
        -> simular el AFN con la cadena w y responder si / no

Formato del archivo de entrada, una linea por caso:

    expresion ; cadena

Si no se escribe el punto y coma se asume que la cadena w es vacia.
Las lineas en blanco y las que empiezan con // se ignoran.

Uso:
    python3 main.py [archivo.txt] [--mostrar]

    --mostrar   abre cada imagen generada en el visor del sistema
"""

import os
import subprocess
import sys

from shunting_yard import (EPSILON, tokenizar, insertar_concatenacion,
                           shunting_yard, expandir_extensiones)
from arbol_sintactico import construir_arbol, recorrido_preorden, dibujar_arbol
from thompson import thompson, dibujar_afn

LINEA = '-' * 78
CARPETA = 'salida'


def leer_casos(ruta):
    """Devuelve la lista de pares (expresion, cadena) del archivo."""
    with open(ruta, 'r', encoding='utf-8') as archivo:
        lineas = archivo.readlines()

    casos = []
    for linea in lineas:
        texto = linea.rstrip('\n').rstrip('\r')
        if texto.strip() == '' or texto.lstrip().startswith('//'):
            continue
        if ';' in texto:
            expresion, cadena = texto.split(';', 1)
            casos.append((expresion.strip(), cadena.strip()))
        else:
            casos.append((texto.strip(), ''))
    return casos


def mostrar_en_pantalla(ruta):
    """Abre la imagen con el visor por defecto del sistema operativo."""
    try:
        if sys.platform.startswith('win'):
            os.startfile(ruta)
        elif sys.platform == 'darwin':
            subprocess.run(['open', ruta], check=False)
        else:
            subprocess.run(['xdg-open', ruta], check=False)
    except Exception:
        print('      (no se pudo abrir el visor; la imagen quedo en ' + ruta + ')')


def imprimir_tabla(afn):
    print('  Tabla de transiciones del AFN:')
    print('      {0:<18} | {1:<8} | {2}'.format('Estado', 'Simbolo', 'Destinos'))
    print('      ' + '-' * 18 + '-|-' + '-' * 8 + '-|-' + '-' * 20)
    for estado, etiqueta, destinos in afn.tabla_transiciones():
        marca = ''
        if estado == afn.inicial:
            marca = ' (inicial)'
        if estado == afn.aceptacion:
            marca = ' (aceptacion)'
        print('      {0:<18} | {1:<8} | {2}'.format(
            str(estado) + marca, etiqueta,
            ', '.join(str(d) for d in destinos)))
    print()


def imprimir_traza(traza):
    print('  Simulacion paso a paso (conjunto de estados posibles):')
    for paso, (entrada, conjunto) in enumerate(traza):
        if paso == 0:
            descripcion = 'cerradura-e del estado inicial'
        else:
            descripcion = "lee '" + entrada + "'"
        if conjunto:
            conjunto_texto = '{' + ', '.join(str(e) for e in conjunto) + '}'
        else:
            conjunto_texto = 'vacio (la cadena se rechaza aqui)'
        print('      {0:<32} {1}'.format(descripcion, conjunto_texto))
    print()


def procesar(numero, expresion, cadena, mostrar):
    print(LINEA)
    print(' CASO {0}'.format(numero))
    print('   r = ' + expresion)
    print('   w = ' + (cadena if cadena else '(cadena vacia)'))
    print(LINEA)

    tokens, error = tokenizar(expresion)
    if error is not None:
        print('  ERROR al tokenizar: ' + error)
        print()
        return False

    tokens = insertar_concatenacion(tokens)
    postfix, _, error = shunting_yard(tokens)
    if error is not None:
        print('  ERROR en shunting yard: ' + error)
        print()
        return False

    expandida, cambios = expandir_extensiones(postfix)
    if expandida is None:
        print('  ERROR: el postfix quedo mal formado al expandir las extensiones')
        print()
        return False

    print('  Postfix:            ' + ' '.join(postfix))
    for c in cambios:
        print('  Reescritura:        ' + c)
    print('  Postfix expandido:  ' + ' '.join(expandida))
    print()

    raiz = construir_arbol(expandida)
    print('  Arbol sintactico:   ' + recorrido_preorden(raiz))

    ruta_arbol = dibujar_arbol(raiz, 'arbol_{0}'.format(numero), CARPETA)
    print('  Imagen del arbol:   ' + ruta_arbol)
    print()

    afn = thompson(raiz, expresion)
    print('  AFN de Thompson:')
    print('      estados:           {0}  (numerados de 0 a {1})'.format(
        len(afn.estados()), len(afn.estados()) - 1))
    print('      estado inicial:    ' + str(afn.inicial))
    print('      estado aceptacion: ' + str(afn.aceptacion))
    print('      alfabeto:          ' + ', '.join(afn.alfabeto()))
    print('      transiciones ' + EPSILON + ':   se listan en la tabla')
    print()

    imprimir_tabla(afn)

    ruta_afn = dibujar_afn(afn, 'afn_{0}'.format(numero), CARPETA)
    print('  Imagen del AFN:     ' + ruta_afn)
    print()

    if mostrar:
        mostrar_en_pantalla(ruta_arbol)
        mostrar_en_pantalla(ruta_afn)

    aceptada, traza = afn.simular(cadena)
    imprimir_traza(traza)

    print('  w ' + ('pertenece' if aceptada else 'NO pertenece') + ' a L(r)')
    print('  RESPUESTA: ' + ('si' if aceptada else 'no'))
    print()
    return True


def main():
    argumentos = [a for a in sys.argv[1:] if not a.startswith('--')]
    mostrar = '--mostrar' in sys.argv

    ruta = argumentos[0] if argumentos else 'expresiones.txt'

    try:
        casos = leer_casos(ruta)
    except FileNotFoundError:
        print('ERROR: no se encontro el archivo ' + ruta)
        sys.exit(1)

    print()
    print(LINEA)
    print(' LABORATORIO 4  -  ALGORITMO DE THOMPSON Y SIMULACION DEL AFN')
    print(' Archivo procesado: ' + ruta)
    print(LINEA)
    print()

    procesados = 0
    for numero, (expresion, cadena) in enumerate(casos, start=1):
        if procesar(numero, expresion, cadena, mostrar):
            procesados += 1

    print(LINEA)
    print(' RESUMEN: {0} de {1} casos procesados correctamente'.format(
        procesados, len(casos)))
    print(' Las imagenes quedaron en la carpeta ' + CARPETA + '/')
    print(LINEA)
    print()


if __name__ == '__main__':
    main()
