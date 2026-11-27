"""
Runs sequential / static / dynamic benchmarks across worker counts.
Writes one CSV per strategy to data/output/.
Run: python experiment.py
"""

import os
import time
import numpy as np
import pandas as pd

import core

IN_PATH  = os.path.join("data", "input",  "numbers.npy")
OUT_DIR  = os.path.join("data", "output")
CHUNKSIZE = 10_000           # for dynamic scheduling
WORKER_COUNTS = [1, 2, 4]    # cap at your logical CPU count


def aggregate(results: list, strategy: str, num_workers: int, wall: float):
    """Per-chunk rows -> one row per (strategy, worker_pid)."""
    df = pd.DataFrame(results)
    return (
        df.groupby("pid", as_index=False)
          .agg(n_chunks  = ("chunk_id", "count"),
               n_items   = ("n_items",  "sum"),
               n_primes  = ("n_primes", "sum"),
               busy_time = ("busy_time","sum"))
          .assign(strategy     = strategy,
                  num_workers  = num_workers,
                  wall_time    = wall,
                  total_primes = int(df["n_primes"].sum()))
    )


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    arr = np.load(IN_PATH).tolist()
    print(f"[experiment] loaded {len(arr):,} items from {IN_PATH}")
    print(f"[experiment] logical cores = {os.cpu_count()}\n")

    # -------- sequential baseline (one run) --------
    print("[experiment] running sequential baseline...")
    seq_res, t_seq = core.run_sequential(arr)
    seq_primes = seq_res[0]["n_primes"]
    print(f"[experiment] sequential: {t_seq:.3f}s  primes={seq_primes:,}\n")

    seq_row = pd.DataFrame([{
        "strategy":     "sequential",
        "num_workers":  1,
        "wall_time":    t_seq,
        "total_primes": seq_primes,
    }])

    static_rows, dynamic_rows = [], []

    # -------- sweep worker counts --------
    for w in WORKER_COUNTS:
        print(f"[experiment] workers={w} ...")

        # static
        s_res, t_s = core.run_static(arr, w)
        s = aggregate(s_res, "static", w, t_s)
        assert s["total_primes"].iloc[0] == seq_primes, "STATIC mismatch!"
        static_rows.append(s)
        print(f"   static : {t_s:.3f}s  speedup={t_seq/t_s:.2f}x")

        # dynamic
        d_res, t_d = core.run_dynamic(arr, w, chunksize=CHUNKSIZE)
        d = aggregate(d_res, "dynamic", w, t_d)
        assert d["total_primes"].iloc[0] == seq_primes, "DYNAMIC mismatch!"
        dynamic_rows.append(d)
        print(f"   dynamic: {t_d:.3f}s  speedup={t_seq/t_d:.2f}x")

    # -------- save --------
    pd.concat(static_rows).to_csv(
        os.path.join(OUT_DIR, "static_results.csv"), index=False)
    pd.concat(dynamic_rows).to_csv(
        os.path.join(OUT_DIR, "dynamic_results.csv"), index=False)
    seq_row.to_csv(
        os.path.join(OUT_DIR, "sequential_results.csv"), index=False)

    print(f"\n[experiment] wrote 3 CSVs to {OUT_DIR}/")
    print("[experiment] equivalence: sequential == static == dynamic  ✔")


if __name__ == "__main__":
    main()