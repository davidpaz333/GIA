"""
Tests de propiedades (property-based testing) para LWWElementSet.

Mismas 4 propiedades que en test_pn_counter.py:
  1. Conmutatividad
  2. Asociatividad
  3. Idempotencia
  4. Monotonicidad (la que pide añadir el correo)
"""

from hypothesis import given, strategies as st

from lww_element_set import LWWElementSet

# Alfabeto pequeño a propósito: con pocos elementos distintos, Hypothesis
# genera muchos más casos con add/remove repetidos sobre el MISMO
# elemento, que es justo el escenario interesante para un LWW-Set
# (donde importa el orden temporal de altas y bajas).
ELEMENTS = ["a", "b", "c"]

element_strategy = st.sampled_from(ELEMENTS)
op_strategy = st.sampled_from(["add", "remove"])
ops_strategy = st.lists(st.tuples(op_strategy, element_strategy), max_size=20)


def build_set(ops: list[tuple[str, str]]) -> LWWElementSet:
    s = LWWElementSet()
    for op, element in ops:
        if op == "add":
            s.add(element)
        else:
            s.remove(element)
    return s


@given(ops1=ops_strategy, ops2=ops_strategy)
def test_merge_is_commutative(ops1, ops2):
    a = build_set(ops1)
    b = build_set(ops2)
    assert a.merge(b) == b.merge(a)


@given(ops1=ops_strategy, ops2=ops_strategy, ops3=ops_strategy)
def test_merge_is_associative(ops1, ops2, ops3):
    a = build_set(ops1)
    b = build_set(ops2)
    c = build_set(ops3)
    assert a.merge(b).merge(c) == a.merge(b.merge(c))


@given(ops1=ops_strategy)
def test_merge_is_idempotent(ops1):
    a = build_set(ops1)
    assert a.merge(a) == a


@given(ops1=ops_strategy, ops2=ops_strategy)
def test_merge_is_monotonic(ops1, ops2):
    """La propiedad que el correo pide añadir esta semana."""
    a = build_set(ops1)
    b = build_set(ops2)
    merged = a.merge(b)
    assert a <= merged, "merge no domina al operando izquierdo (A o R encogen)"
    assert b <= merged, "merge no domina al operando derecho (A o R encogen)"
def test_concurrent_add_and_remove_same_element_add_wins_on_strict_later_timestamp():
    """Test de escenario explícito (no property-based): comprueba el caso
    más delicado del LWW-Element-Set, que las 4 propiedades algebraicas
    de arriba NO verifican por sí solas: que conmutatividad, asociatividad,
    idempotencia y monotonicidad se cumplan no dice nada sobre CUÁL de los
    dos valores concurrentes termina "ganando".

    Regla documentada en lww_element_set.py (sección 3.3.3 del paper):
    lookup(e) = exists t, forall t' > t : (e,t) in A and (e,t') not in R
    Es decir: en caso de empate exacto de timestamp, remove gana (hace
    falta un timestamp de add ESTRICTAMENTE mayor para seguir en el set).

    Aquí forzamos el caso real de interés: add() después de remove(),
    en réplicas separadas, fusionadas después. Con nuestro _Clock global
    compartido, basta con llamar add() en último lugar para garantizarle
    un timestamp mayor.
    """
    replica_a = LWWElementSet()
    replica_b = LWWElementSet()

    replica_a.add("libro")
    assert replica_a.lookup("libro") is True

    replica_b.remove("libro")  # remove concurrente, en otra réplica,
    #                            SIN haber visto el add de replica_a

    # Alguien, más tarde, vuelve a añadir el mismo elemento:
    replica_a.add("libro")  # timestamp estrictamente mayor que el remove

    merged = replica_a.merge(replica_b)

    assert merged.lookup("libro") is True, (
        "el add más reciente debería ganar sobre el remove anterior"
    )