"""
Configuración común de pytest/Hypothesis para los tests de propiedades
de los CRDTs (TFG1 - banco de pruebas y framework de evaluación).

Fijamos un perfil "reproducible" con derandomize=True: Hypothesis deja
de usar aleatoriedad real y genera siempre la MISMA secuencia de casos
de prueba en cada ejecución, en cualquier máquina. Es el equivalente a
fijar una semilla, pero vive en el código en vez de depender de que
alguien recuerde pasar --hypothesis-seed=... a mano.

Referencia: https://hypothesis.readthedocs.io/en/latest/settings.html
"""

from hypothesis import settings

settings.register_profile(
    "reproducible",
    derandomize=True,   # misma secuencia de casos siempre, sin semilla manual
    max_examples=200,   # nº de casos generados por test; subir si da tiempo
    print_blob=True,    # si un test falla, imprime el caso exacto para reproducirlo
)
settings.load_profile("reproducible")
