"""
Reúne en un único JSON las métricas estáticas de radon y ruff sobre el
código CRDT (TFG2).

- radon (API de Python): complejidad ciclomática por bloque e índice de
  mantenibilidad por fichero.
- ruff (CLI, vía `python -m ruff`): avisos de las familias de reglas
  indicadas en RULES.

Las rutas de ruff se normalizan a relativas: ruff las devuelve absolutas,
con el nombre de usuario de quien ejecuta, y eso no es portable.

Uso:
    python collect_static_metrics.py                      # ficheros por defecto
    python collect_static_metrics.py a.py b.py -o out.json
"""

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from importlib.metadata import version
from pathlib import Path

from radon.complexity import cc_rank, cc_visit
from radon.metrics import mi_rank, mi_visit

DEFAULT_FILES = ["pn_counter.py", "lww_element_set.py"]
RULES = "E,F,W,B,SIM,C90,PL"


def radon_metrics(path: Path) -> dict:
    code = path.read_text(encoding="utf-8")

    # cc_visit devuelve los bloques de primer nivel (funciones, métodos y
    # clases). Los métodos de una clase también cuelgan de class.methods:
    # ahí es donde el JSON de la CLI los duplica. Aquí solo se recorren los
    # bloques de primer nivel, así que no hay duplicados.
    blocks = []
    for b in cc_visit(code):
        blocks.append(
            {
                "kind": b.letter,  # M método, C clase, F función
                "name": getattr(b, "fullname", b.name),
                "lineno": b.lineno,
                "complexity": b.complexity,
                "rank": cc_rank(b.complexity),
            }
        )
    blocks.sort(key=lambda x: x["lineno"])

    mi = mi_visit(code, multi=True)
    complexities = [b["complexity"] for b in blocks]
    return {
        "maintainability_index": round(mi, 2),
        "maintainability_rank": mi_rank(mi),
        "blocks_analyzed": len(blocks),
        "average_complexity": round(sum(complexities) / len(complexities), 2),
        "max_complexity": max(complexities),
        "blocks": blocks,
    }


def ruff_metrics(files: list[str]) -> dict:
    # ruff devuelve código de salida 1 cuando encuentra avisos: no es un error.
    proc = subprocess.run(
        [sys.executable, "-m", "ruff", "check", *files,
         "--select", RULES, "--output-format", "json"],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"ruff falló (código {proc.returncode}): {proc.stderr}")

    raw = json.loads(proc.stdout or "[]")
    violations = [
        {
            "file": os.path.relpath(v["filename"]),
            "code": v["code"],
            "name": v["name"],
            "line": v["location"]["row"],
            "message": v["message"],
            "fix_applicability": (v["fix"] or {}).get("applicability"),
        }
        for v in raw
    ]
    return {
        "rules_selected": RULES,
        "total": len(violations),
        "by_code": dict(sorted(Counter(v["code"] for v in violations).items())),
        "violations": violations,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", default=DEFAULT_FILES)
    ap.add_argument("-o", "--output", default="static_metrics.json")
    args = ap.parse_args()

    result = {
        "tools": {"radon": version("radon"), "ruff": version("ruff")},
        "radon": {f: radon_metrics(Path(f)) for f in args.files},
        "ruff": ruff_metrics(args.files),
    }
    Path(args.output).write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Escrito {args.output}")
    for f, m in result["radon"].items():
        print(f"  {f}: MI {m['maintainability_index']} ({m['maintainability_rank']}), "
              f"{m['blocks_analyzed']} bloques, media {m['average_complexity']}, "
              f"máx {m['max_complexity']}")
    print(f"  ruff: {result['ruff']['total']} avisos {result['ruff']['by_code']}")


if __name__ == "__main__":
    main()
