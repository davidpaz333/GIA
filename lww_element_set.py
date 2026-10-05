"""
LWW-Element-Set (state-based) — CvRDT

Fuente: Shapiro, Preguiça, Baquero, Zawirski, "A comprehensive study of
Convergent and Commutative Replicated Data Types", INRIA RR-7506, 2011.
Sección 3.3.3 (p. 24) y Figura 12 (p. 24).

A diferencia del PN-Counter, el paper NO da una caja "Specification N"
con pseudocódigo formal para este tipo: lo describe de forma narrativa.
Esta implementación traduce esa descripción literalmente:

    "Consider add-set A and remove-set R, each containing (element,
    timestamp) pairs. To add (resp. remove) an element e, add the pair
    (e, now()) [...] to A (resp. to R). Merging two replicas takes the
    union of their add-sets and remove-sets. An element e is in the set
    if it is in A, and it is not in R with a higher timestamp:
    lookup(e) = exists t, forall t' > t : (e, t) in A and (e, t') not in R."

Puntos importantes heredados del propio texto del paper (a tener en
cuenta en los tests de propiedades, sección "puntos calientes"):

    - `now()` debe generar timestamps ÚNICOS y CONSISTENTES CON LA
      CAUSALIDAD (igual que en LWW-Register, Specification 8, nota de
      la línea 4: "Timestamp, consistent with causality"). Si dos
      réplicas generan el mismo timestamp para una add y una remove
      concurrentes del mismo elemento, el resultado es "opaco": el
      propio paper señala esto como la limitación central de todo el
      enfoque LWW (ver comparación con OR-Set en la sección 3.3.5).
    - merge es la UNIÓN de los conjuntos A y R completos, no un max
      por elemento: por eso A y R solo crecen (monótonos), lo cual es
      coherente con que sea un CvRDT (semirretículo de unión).
    - Esta implementación usa "remove gana en empate" (t' > t estricto
      para seguir en el set) tal como está escrito en el paper. Es una
      decisión de diseño explícita del propio texto, no nuestra.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from itertools import count


class _Clock:
    """Generador de timestamps únicos y monótonos, válido como `now()`
    siempre que todas las operaciones de una misma réplica sean locales
    y secuenciales (consistencia con causalidad local, no global)."""

    _counter = count(1)

    @classmethod
    def now(cls) -> int:
        return next(cls._counter)


@dataclass
class LWWElementSet:
    """payload: add-set A y remove-set R, cada uno un conjunto de pares
    (elemento, timestamp)."""

    A: set[tuple] = field(default_factory=set)  # add-set
    R: set[tuple] = field(default_factory=set)  # remove-set

    # --- update add(e) ------------------------------------------------
    # "add the pair (e, now()) ... to A"
    def add(self, element) -> None:
        self.A.add((element, _Clock.now()))

    # --- update remove(e) ----------------------------------------------
    # "add the pair (e, now()) ... to R"
    def remove(self, element) -> None:
        self.R.add((element, _Clock.now()))

    # --- query lookup(e) : boolean -------------------------------------
    # lookup(e) = exists t, forall t' > t : (e, t) in A and (e, t') not in R
    """osea que por asi decirlo A y R son subconjuntos que "alimentan" a un super conjunto, 
    cuando llega un elemento, se compara si hay una marca de tiempo en A y 
    si la marca de A es mayor que la de R (no ha sido eleminado), no entiendo 
    pq comprueba que tiene marca de tiempo en A"""

    """Se comprueba que el elemento tiene una marca de tiempo en A porque, 
    para que un elemento pueda estar en el conjunto lógico resultante, primero debe haber sido agregado."""
    def lookup(self, element) -> bool:
        add_times = [t for (e, t) in self.A if e == element]
        if not add_times:
            return False
        last_add = max(add_times)
        remove_times = [t for (e, t) in self.R if e == element]
        last_remove = max(remove_times) if remove_times else -1
        return last_add > last_remove

    # --- query elements() : set -----------------------------------------
    # Conveniencia: el conjunto "lógico" completo, no parte del paper
    # pero necesaria para comparar snapshots en los tests.
    def elements(self) -> set:
        candidates = {e for (e, _t) in self.A}
        return {e for e in candidates if self.lookup(e)}

    # --- merge(X, Y) : payload Z ------------------------------------------
    # "Merging two replicas takes the union of their add-sets and
    # remove-sets."
    def merge(self, other: "LWWElementSet") -> "LWWElementSet":
        return LWWElementSet(A=self.A | other.A, R=self.R | other.R)

    # --- compare(X, Y) : boolean -----------------------------------------
    # No está explícito en el texto para este tipo, pero se deriva
    # directamente de ser union-semilattice: X <= Y si X.A subset Y.A
    # y X.R subset Y.R (igual patrón que G-Set/2P-Set, Specs 10 y 11).
    def __le__(self, other: "LWWElementSet") -> bool:
        return self.A <= other.A and self.R <= other.R

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LWWElementSet):
            return NotImplemented
        return self.A == other.A and self.R == other.R


# --- propiedades CRDT a verificar con Hypothesis ---------------------------
#
# 1. Conmutatividad de merge:      a.merge(b) == b.merge(a)
# 2. Asociatividad de merge:       a.merge(b).merge(c) == a.merge(b.merge(c))
# 3. Idempotencia de merge:        a.merge(a) == a
# 4. Monotonicidad (la que falta): tras cualquier add/remove/merge, el
#    nuevo estado contiene (como subconjunto, via __le__) al estado
#    anterior — A y R nunca encogen.
#
# CUIDADO al escribir estos tests con una sola _Clock global compartida
# entre "réplicas" simuladas en el mismo proceso: si queréis simular
# relojes independientes por réplica (más realista, más cercano a lo
# que exige el paper sobre consistencia causal), sustituid _Clock.now()
# por un reloj lógico por instancia (p. ej. (replica_id, contador_local)
# con orden lexicográfico) en vez de un contador global de módulo.
