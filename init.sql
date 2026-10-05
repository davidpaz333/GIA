CREATE TABLE IF NOT EXISTS test_runs (
    id                 SERIAL PRIMARY KEY,
    run_timestamp      TIMESTAMPTZ NOT NULL DEFAULT now(),
    test_name          TEXT NOT NULL,
    outcome            TEXT NOT NULL,
    duration_seconds   NUMERIC NOT NULL,
    hypothesis_derandomize  BOOLEAN,
    hypothesis_max_examples INTEGER
);

CREATE INDEX IF NOT EXISTS idx_test_runs_name_time
    ON test_runs (test_name, run_timestamp);