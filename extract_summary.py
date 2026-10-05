"""
Extrae de results.json (salida cruda de pytest-json-report) un resumen
limpio: solo lo que hace falta para la tabla del entregable de TFG1.

Uso:
    python extract_summary.py results.json summary.json
"""

import json
import sys
from pathlib import Path


def summarize(raw: dict) -> dict:
    return {
        "exit_ok": raw["exitcode"] == 0,
        "duration_seconds": round(raw["duration"], 3),
        "summary": raw["summary"],
        "hypothesis_profile": {
            # Estos campos no vienen en el JSON de pytest-json-report
            # tal cual; los fijamos aquí a mano porque son constantes
            # (vienen de conftest.py), así queda documentado junto al
            # resultado qué configuración se usó para generarlo.
            "derandomize": True,
            "max_examples": 200,
        },
        "tests": [
            {
                "name": t["nodeid"],
                "outcome": t["outcome"],
                "duration_seconds": round(t["call"]["duration"], 4),
            }
            for t in raw["tests"]
        ],
    }


if __name__ == "__main__":
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "results.json")
    dst = Path(sys.argv[2] if len(sys.argv) > 2 else "summary.json")

    raw = json.loads(src.read_text(encoding="utf-8"))
    clean = summarize(raw)
    dst.write_text(json.dumps(clean, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Resumen escrito en {dst}")
    print(json.dumps(clean["summary"], indent=2))
