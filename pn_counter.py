"""
PN-Counter (state-based) — CvRDT

Fuente: Shapiro, Preguiça, Baquero, Zawirski, "A comprehensive study of
Convergent and Commutative Replicated Data Types", INRIA RR-7506, 2011.
Sección 3.1.3, Specification 7 (p. 16).

Combina dos G-Counters (Specification 6): un vector P para incrementos y
un vector N para decrementos, uno por réplica. El valor es sum(P) - sum(N).
merge toma el máximo componente a componente de cada vector, por lo que
calcula siempre la cota superior mínima (LUB) del semirretículo producto
P x N. Dado que merge es la LUB, PN-Counter es un CvRDT.

Supuestos heredados del paper (ver sección 3.1.2):
    - El conjunto de réplicas es conocido de antemano (tamaño fijo n).
    - No hay overflow en los contadores.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class PNCounter:
    """Un PN-Counter para un conjunto fijo de `n` réplicas.

    `replica_id` identifica qué entrada de P y N pertenece a esta réplica
    (línea 4-5 y 7-8 de la Specification 7: `let g = myID()`).
    """

    n: int
    replica_id: int
    P: list[int] = field(default_factory=list)
    N: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not (0 <= self.replica_id < self.n):
            raise ValueError("replica_id debe estar en [0, n-1]")
        # initial [0, 0, ..., 0], [0, 0, ..., 0]  (línea 2)
        if not self.P:
            self.P = [0] * self.n
        if not self.N:
            self.N = [0] * self.n
        if len(self.P) != self.n or len(self.N) != self.n:
            raise ValueError("P y N deben tener longitud n")

    # --- update increment() -------------------------------------------
    # líneas 3-5: P[g] := P[g] + 1
    def increment(self) -> None:
        self.P[self.replica_id] += 1

    # --- update decrement() -------------------------------------------
    # líneas 6-8: N[g] := N[g] + 1
    def decrement(self) -> None:
        self.N[self.replica_id] += 1

    # --- query value() ---------------------------------------------------
    # línea 9-10: v = sum(P) - sum(N)
    def value(self) -> int:
        return sum(self.P) - sum(self.N)

    # --- compare(X, Y) ---------------------------------------------------
    # línea 11-12: orden parcial = conjunción de ambos G-Counters
    def __le__(self, other: "PNCounter") -> bool:
        if self.n != other.n:
            raise ValueError("solo se pueden comparar contadores del mismo n")
        return all(p1 <= p2 for p1, p2 in zip(self.P, other.P)) and all(
            n1 <= n2 for n1, n2 in zip(self.N, other.N)
        )

    # --- merge(X, Y) : payload Z ------------------------------------------
    # líneas 13-15: Z.P[i] = max(X.P[i], Y.P[i]); Z.N[i] = max(X.N[i], Y.N[i])
    def merge(self, other: "PNCounter") -> "PNCounter":
        if self.n != other.n:
            raise ValueError("solo se pueden fusionar contadores del mismo n")
        merged = PNCounter(
            n=self.n,
            replica_id=self.replica_id,
            P=[max(a, b) for a, b in zip(self.P, other.P)],
            N=[max(a, b) for a, b in zip(self.N, other.N)],
        )
        return merged

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PNCounter):
            return NotImplemented
        return self.n == other.n and self.P == other.P and self.N == other.N


# --- propiedades CRDT a verificar con Hypothesis ---------------------------
# (útiles como lista de chequeo para TFG1, sección "añadir monotonicidad")
#
# 1. Conmutatividad de merge:      a.merge(b) == b.merge(a)
# 2. Asociatividad de merge:       a.merge(b).merge(c) == a.merge(b.merge(c))
# 3. Idempotencia de merge:        a.merge(a) == a
# 4. Monotonicidad (la que falta): tras cualquier update local o merge,
#    el nuevo estado X' cumple X <= X' según __le__ (nunca se retrocede
#    en el semirretículo). Es decir:
#       before = PNCounter(...)
#       ... increment()/decrement()/merge() ...
#       assert before <= after
