"""
Tests de propiedades (property-based testing) para PNCounter.

Las 4 propiedades que debe cumplir cualquier CvRDT (ver pn_counter.py,
sección final del fichero, y Shapiro et al. 2011 secc. 2.3):

  1. Conmutatividad:  a.merge(b) == b.merge(a)
  2. Asociatividad:   a.merge(b).merge(c) == a.merge(b.merge(c))
  3. Idempotencia:    a.merge(a) == a
  4. Monotonicidad:   a <= a.merge(b)  y  b <= a.merge(b)
                       (el merge nunca "retrocede": domina a ambos
                       operandos en el semirretículo, es decir, es
                       efectivamente la LUB)
"""

from hypothesis import given, assume, strategies as st

from pn_counter import PNCounter

N_REPLICAS = 4  # nº fijo de réplicas para todos los tests de este fichero


# --- estrategia: generar un PNCounter aplicando una secuencia aleatoria
#     de increment()/decrement() sobre una réplica concreta -----------------
def build_counter(replica_id: int, ops: list[str]) -> PNCounter:
    c = PNCounter(n=N_REPLICAS, replica_id=replica_id)
    for op in ops:
        if op == "inc":
            c.increment()
        else:
            c.decrement()
    return c


replica_id_strategy = st.integers(min_value=0, max_value=N_REPLICAS - 1)
ops_strategy = st.lists(st.sampled_from(["inc", "dec"]), max_size=20)


@given(r1=replica_id_strategy, ops1=ops_strategy,
       r2=replica_id_strategy, ops2=ops_strategy)
def test_merge_is_commutative(r1, ops1, r2, ops2):
    a = build_counter(r1, ops1)
    b = build_counter(r2, ops2)
    assert a.merge(b) == b.merge(a)


@given(r1=replica_id_strategy, ops1=ops_strategy,
       r2=replica_id_strategy, ops2=ops_strategy,
       r3=replica_id_strategy, ops3=ops_strategy)
def test_merge_is_associative(r1, ops1, r2, ops2, r3, ops3):
    a = build_counter(r1, ops1)
    b = build_counter(r2, ops2)
    c = build_counter(r3, ops3)
    assert a.merge(b).merge(c) == a.merge(b.merge(c))


@given(r1=replica_id_strategy, ops1=ops_strategy)
def test_merge_is_idempotent(r1, ops1):
    a = build_counter(r1, ops1)
    assert a.merge(a) == a


@given(r1=replica_id_strategy, ops1=ops_strategy,
       r2=replica_id_strategy, ops2=ops_strategy)
def test_merge_is_monotonic(r1, ops1, r2, ops2):
    """La propiedad que el correo pide añadir esta semana."""
    a = build_counter(r1, ops1)
    b = build_counter(r2, ops2)
    merged = a.merge(b)
    assert a <= merged, "merge no domina al operando izquierdo"
    assert b <= merged, "merge no domina al operando derecho"


@given(r1=replica_id_strategy, ops1=ops_strategy,
       r2=replica_id_strategy, ops2=ops_strategy)
def test_value_after_merge_matches_independent_updates(r1, ops1, r2, ops2):
    """Chequeo semántico extra (no es una de las 4 propiedades CRDT,
    pero vale la pena tenerlo): el valor tras el merge coincide con
    aplicar todos los incrementos/decrementos de ambas réplicas.

    Solo tiene sentido cuando r1 != r2: si fueran la misma réplica,
    merge hace max() sobre esa entrada del vector, no suma las dos
    historias (ver PNCounter.merge, línea 13-15 de la Specification 7)
    - dos historias divergentes en la MISMA entrada no es un escenario
    que el modelo represente, así que lo descartamos con assume().
    """
    assume(r1 != r2)
    a = build_counter(r1, ops1)
    b = build_counter(r2, ops2)
    merged = a.merge(b)

    expected = 0
    for op in ops1 + ops2:
        expected += 1 if op == "inc" else -1
    assert merged.value() == expected
