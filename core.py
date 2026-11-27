"""
Core parallel-processing logic.

All worker functions are module-level (required for Windows 'spawn').
No side effects on import -> safe to import from any script/notebook.
"""

import time
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed


# ------------------------------------------------------------------
# Workload: prime counting
# ------------------------------------------------------------------
def is_prime(n: int) -> bool:
    """Naive trial division. Cost grows with n -> natural skew."""
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


def process_chunk(chunk_id: int, chunk: list) -> dict:
    """
    Runs inside a worker process.
    Returns observable stats -> proves real parallelism, real work.
    """
    pid = mp.current_process().pid
    t0 = time.perf_counter()
    n_primes = sum(1 for x in chunk if is_prime(x))
    busy = time.perf_counter() - t0
    return {
        "chunk_id":   chunk_id,
        "pid":        pid,
        "n_items":    len(chunk),
        "n_primes":   n_primes,
        "busy_time":  busy,
    }


# ------------------------------------------------------------------
# Sequential baseline
# ------------------------------------------------------------------
def run_sequential(arr: list) -> tuple[list, float]:
    """Single-process baseline. Uses same worker fn for fair comparison."""
    t0 = time.perf_counter()
    result = process_chunk(0, arr)
    return [result], time.perf_counter() - t0


# ------------------------------------------------------------------
# Static scheduling: N equal partitions, one per worker, up front
# ------------------------------------------------------------------
def run_static(arr: list, num_workers: int) -> tuple[list, float]:
    n = len(arr)
    step = (n + num_workers - 1) // num_workers
    chunks = [
        (i, arr[i * step : (i + 1) * step])
        for i in range(num_workers)
    ]
    chunks = [(i, c) for i, c in chunks if c]  # drop empty tails

    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=num_workers) as ex:
        futs = [ex.submit(process_chunk, cid, c) for cid, c in chunks]
        results = [f.result() for f in futs]
    return results, time.perf_counter() - t0


# ------------------------------------------------------------------
# Dynamic scheduling: many small chunks, pool pulls next when free
# ------------------------------------------------------------------
def run_dynamic(arr: list, num_workers: int,
                chunksize: int = 10_000) -> tuple[list, float]:
    chunks = [
        (i, arr[i : i + chunksize])
        for i in range(0, len(arr), chunksize)
    ]

    t0 = time.perf_counter()
    results = []
    with ProcessPoolExecutor(max_workers=num_workers) as ex:
        futs = {ex.submit(process_chunk, cid, c): cid for cid, c in chunks}
        for f in as_completed(futs):
            results.append(f.result())
    return results, time.perf_counter() - t0