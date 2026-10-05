"""
Carga summary.json (generado por extract_summary.py) en la tabla
test_runs de PostgreSQL, una fila por test de esa ejecución.

Requiere psycopg2-binary (versión fijada, ver pip install abajo) y que
el contenedor de docker-compose.yml esté arrancado.

Uso:
    python load_results_to_postgres.py summary.json
"""

import json
import sys
from pathlib import Path

import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "crdt_benchmarks",
    "user": "crdt",
    "password": "crdt_dev_password",  # debe coincidir con docker-compose.yml
}

INSERT_SQL = """
    INSERT INTO test_runs
        (test_name, outcome, duration_seconds,
         hypothesis_derandomize, hypothesis_max_examples)
    VALUES (%s, %s, %s, %s, %s)
"""


def load(summary_path: Path) -> int:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    profile = summary["hypothesis_profile"]

    rows = [
        (
            t["name"],
            t["outcome"],
            t["duration_seconds"],
            profile["derandomize"],
            profile["max_examples"],
        )
        for t in summary["tests"]
    ]

    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.executemany(INSERT_SQL, rows)
        conn.commit()

    return len(rows)


if __name__ == "__main__":
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "summary.json")
    n = load(path)
    print(f"{n} filas insertadas en test_runs a partir de {path}")