# TFG1 - Primeras pruebas con las herramientas del arnés

Repositorio provisional. Se pasará al repositorio UC3M-GMV de la organización GIAA-UC3M cuando esté creado.

Banco de pruebas: PN-Counter y LWW-Element-Set, implementados a partir de Shapiro et al. (2011), *A comprehensive study of Convergent and Commutative Replicated Data Types*:

- PN-Counter: Specification 7 (sección 3.1.3), traducción literal.
- LWW-Element-Set: el paper lo describe solo en prosa (sección 3.3.3), así que la traducción a código es propia. El reloj lógico (`_Clock`) es una decisión de implementación, no del paper.

## Contenido

| Fichero | Qué es |
|---|---|
| `pn_counter.py`, `lww_element_set.py` | Código bajo prueba |
| `conftest.py` | Perfil de Hypothesis reproducible (`derandomize=True`, 200 ejemplos) |
| `test_pn_counter.py`, `test_lww_element_set.py` | Tests de propiedades (conmutatividad, asociatividad, idempotencia, monotonicidad) y tests semánticos |
| `extract_summary.py` | Reduce `results.json` a un `summary.json` limpio |
| `load_results_to_postgres.py` | Carga `summary.json` en la tabla `test_runs` |
| `docker-compose.yml`, `init.sql` | PostgreSQL 16.4 y su tabla (extra opcional) |
| `Tabla_comun_herramientas.xlsx` | Tabla del entregable: versión, qué mide, formato de salida y limitaciones |

## Puesta en marcha (Windows)

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecutar los tests

```cmd
python -m pytest -v --tb=short
```

Deben pasar los 10 tests. La cabecera de pytest tiene que decir `hypothesis profile 'reproducible'`; si dice `'default'`, `conftest.py` no se está cargando.

## Exportar los resultados

```cmd
python -m pytest -v --json-report --json-report-file=results.json
python extract_summary.py results.json summary.json
```

## Guardar los resultados en PostgreSQL (opcional)

Requiere Docker Desktop en marcha.

```cmd
docker compose up -d
docker compose ps
python load_results_to_postgres.py summary.json
```

Consulta:

```cmd
docker exec -it crdt_results_db psql -U crdt -d crdt_benchmarks -c "SELECT test_name, outcome, duration_seconds FROM test_runs;"
```

Las credenciales de `docker-compose.yml` son solo de desarrollo local.

## Comprobación de que los tests detectan bugs

Se introdujeron cinco mutantes a mano (detalle en la segunda hoja de la tabla). Cuatro se detectan y uno sobrevive (`>` por `>=` en `lookup` del LWW-Element-Set), porque el reloj global da timestamps únicos y nunca hay empates.
