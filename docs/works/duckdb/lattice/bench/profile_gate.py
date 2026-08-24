#!/usr/bin/env python3
"""Profile gate for the DuckDB coordinate lattice track.

Phase 1 of the development plan in docs/works/duckdb/lattice. Measures the
incumbent scan and index costs for multi-dimensional point and range queries
over bounded integer dimensions in stock DuckDB (pip package, no C++ build).

Table: lattice_bench(d1, d2, d3, payload) with 215 cubed = 9,938,375 rows,
one row per cell, dimensions uniform in [0, 215), random row order.

Output: bench/results/pre_integration.json and a printed summary.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from pathlib import Path

import duckdb

D = 215
N = D * D * D
SEED = 20260824
RUNS = 7
SELS = [1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1]

PROJECTIONS = {
    "count": "SELECT count(*) FROM lattice_bench WHERE {pred}",
    "payload": "SELECT payload FROM lattice_bench WHERE {pred}",
}


def make_table(con) -> float:
    t0 = time.perf_counter()
    con.execute("DROP TABLE IF EXISTS lattice_bench")
    con.execute(
        f"""
        CREATE TABLE lattice_bench AS
        SELECT (x / {D * D})::INTEGER % {D} AS d1,
               (x / {D})::INTEGER % {D} AS d2,
               (x % {D})::INTEGER AS d3,
               random() AS payload
        FROM range(0, {N}) t(x)
        ORDER BY random()
        """
    )
    return time.perf_counter() - t0


def gen_queries(rng):
    """Return a list of (class, label, predicate, matches)."""
    queries = []

    def add(cls, label, pred, matches):
        queries.append((cls, label, pred, matches))

    r1, r2, r3 = (rng.randrange(D) for _ in range(3))
    add("P2", "point", f"d1 = {r1} AND d2 = {r2}", D)
    add("P3", "point", f"d1 = {r1} AND d2 = {r2} AND d3 = {r3}", 1)

    for sel in SELS:
        side2 = max(1, round((sel * N / D) ** 0.5))
        a = rng.randrange(D - side2 + 1)
        c = rng.randrange(D - side2 + 1)
        add("R2", f"{sel:.0e}", f"d1 BETWEEN {a} AND {a + side2 - 1} AND d2 BETWEEN {c} AND {c + side2 - 1}",
            side2 * side2 * D)

        side3 = max(1, round((sel * N) ** (1 / 3)))
        a = rng.randrange(D - side3 + 1)
        c = rng.randrange(D - side3 + 1)
        e = rng.randrange(D - side3 + 1)
        add("R3", f"{sel:.0e}",
            f"d1 BETWEEN {a} AND {a + side3 - 1} AND d2 BETWEEN {c} AND {c + side3 - 1} AND d3 BETWEEN {e} AND {e + side3 - 1}",
            side3 ** 3)

    x = rng.randrange(D)
    add("S1", "point", f"d1 = {x}", D * D)
    for sel in SELS:
        length = max(1, round(sel * N / (D * D)))
        a = rng.randrange(D - length + 1)
        add("S1", f"{sel:.0e}", f"d1 BETWEEN {a} AND {a + length - 1}", length * D * D)

    return queries


def measure(con, query, matches, runs=RUNS):
    con.execute(query).fetchall()  # warm run
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        con.execute(query).fetchall()
        times.append((time.perf_counter() - t0) * 1000)
    plan = con.execute(f"EXPLAIN (FORMAT JSON, ANALYZE) {query}").fetchall()[0][1]
    root = json.loads(plan)
    scan_rows = 0
    scan_time_ms = 0.0
    stack = [root]
    while stack:
        node = stack.pop()
        if node.get("operator_type") == "TABLE_SCAN":
            scan_rows += node.get("operator_rows_scanned") or 0
            scan_time_ms += (node.get("operator_timing") or 0.0) * 1000
        stack.extend(node.get("children", []))
    return {
        "median_ms": statistics.median(times),
        "min_ms": min(times),
        "max_ms": max(times),
        "matches": matches,
        "actual_sel": matches / N,
        "rows_scanned": scan_rows,
        "scan_time_ms": scan_time_ms,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).parent / "results" / "pre_integration.json"))
    ap.add_argument("--index", action="store_true", help="also measure the ART index baselines (B1)")
    args = ap.parse_args()

    con = duckdb.connect()
    version = con.execute("SELECT version()").fetchone()[0]
    settings = {
        "index_scan_percentage": con.execute("SELECT current_setting('index_scan_percentage')").fetchone()[0],
        "index_scan_max_count": con.execute("SELECT current_setting('index_scan_max_count')").fetchone()[0],
        "threads": con.execute("SELECT current_setting('threads')").fetchone()[0],
    }
    rng = random.Random(SEED)
    queries = gen_queries(rng)

    load_s = make_table(con)
    row_count = con.execute("SELECT count(*) FROM lattice_bench").fetchone()[0]

    results = {
        "phase": "profile_gate",
        "version": version,
        "settings": settings,
        "load_s": load_s,
        "rows": row_count,
        "dims": D,
        "queries": {},
    }

    for cls, label, pred, matches in queries:
        for proj, template in PROJECTIONS.items():
            key = f"B0-{cls}/{label}/{proj}"
            results["queries"][key] = measure(con, template.format(pred=pred), matches)

    if args.index:
        t0 = time.perf_counter()
        for col in ("d1", "d2", "d3"):
            con.execute(f"CREATE INDEX idx_{col} ON lattice_bench({col})")
        results["index_build_s"] = time.perf_counter() - t0

        for cls, label, pred, matches in queries:
            if cls != "S1":
                continue
            for proj, template in PROJECTIONS.items():
                key = f"B1-S1/{label}/{proj}"
                results["queries"][key] = measure(con, template.format(pred=pred), matches)

        q = "SELECT count(*) FROM lattice_bench WHERE d1 = 5 AND d2 = 5"
        results["queries"]["B1-P2/point/count"] = measure(con, q, D)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
