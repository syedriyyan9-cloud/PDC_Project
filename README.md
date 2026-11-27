# Project Name: Parallel Prime Counting: Static vs Dynamic Scheduling

---

# Parallel Prime Counting with Static vs. Dynamic Load Balancing

A Parallel and Distributed Computing (PDC) project demonstrating how workload
scheduling strategy affects performance when a large dataset is processed across
multiple worker processes on a single laptop.

---

## 1. Motivation

The purpose of this project is to demonstrate, empirically and honestly, that:

1. Splitting a large workload across multiple processes can reduce total
   execution time.
2. **How** you split that workload matters. Static partitioning and dynamic
   scheduling produce measurably different load distributions when per-item
   cost is uneven.
3. Parallelism does not scale linearly. Overhead, hyperthreading, and Amdahl's
   Law all impose real ceilings that are visible in the measured data.

The workload chosen to demonstrate this is **prime counting**: for every
integer in `[1, M]`, decide whether it is prime. Prime checking via trial
division costs more for larger numbers, so a contiguous range of integers has
naturally skewed cost — exactly what we need to expose the difference between
static and dynamic scheduling.

---

## 2. What the system does

generate.py → builds an integer array [1..M] and saves it
experiment.py → runs sequential / static / dynamic benchmarks
core.py → Pure computation. No file I/O, no printing, no CLI, no notebook code. Importable and testable in isolation.
analysis.ipynb → loads result CSVs and plots the comparison charts

##### The mental model

core.py ─────► experiment.py ─────► data/output/\*.csv ─────► analysis.ipynb
(the engine) (driver) (raw measurements) (charts)

The pipeline processes **M = 1,000,000 integers**. Sequential execution produces
a reference prime count of **78,498**, which every parallel run is asserted
against to guarantee correctness.

---

## 3. Scheduling strategies compared

### Sequential baseline

A single process iterates over all 1,000,000 integers. Wall-clock time is
recorded and used as the denominator for all speedup measurements.

### Static scheduling

The array is split into **N equal contiguous partitions** up front (one per
worker). Each worker is assigned its partition before execution begins and
processes it in full. The total work per worker is fixed by the partitioning
step, regardless of how long each item actually takes.

### Dynamic scheduling

The array is split into **many small chunks** (chunk size = 10,000). Chunks are
submitted to a `ProcessPoolExecutor`. As soon as a worker finishes a chunk it
pulls the next available one. Fast chunks free a worker to pick up more work,
which self-balances the run when per-chunk cost varies.

The pool's internal task queue **is** the load balancer — no custom queue was
written; `concurrent.futures` handles the pull mechanism. What is measured is
its _effect_, not its implementation.

---

## 4. Measured results (this machine, 4 logical cores)

| Strategy   | Workers | Wall time (s) | Speedup | Efficiency |
| ---------- | ------: | ------------: | ------: | ---------: |
| Sequential |       1 |         10.29 |   1.00× |       100% |
| Static     |       1 |         10.43 |   0.99× |        99% |
| Dynamic    |       1 |          9.81 |   1.05× |       105% |
| Static     |       2 |          6.42 |   1.60× |        80% |
| Dynamic    |       2 |          6.84 |   1.50× |        75% |
| Static     |       4 |          7.28 |   1.41× |        35% |
| Dynamic    |       4 |          6.50 |   1.58× |        40% |

Prime count in every run: **78,498** (identical to sequential — verified by
assertion in `experiment.py`).

### Honest interpretation of these numbers

- **Speedup plateaus around 1.5–1.6×**, not the theoretical 4× a naive reading
  of "4 cores" would suggest. Reasons:
  - Only **2 physical cores** are present; the other 2 logical cores are
    hyperthread siblings. Hyperthreading gives ~10–30% extra throughput, not 2×.
  - On Windows, `multiprocessing` uses `spawn`: each worker re-imports the
    module, which is pure overhead.
  - Amdahl's Law: the array load, CSV write, and process setup are sequential
    and unavoidable.
- **4 workers perform worse than 2 for static scheduling.** This is the
  overhead wall: once per-process setup cost exceeds the parallel gain, adding
  workers regresses performance. This is a _real result_, not a bug.
- **Dynamic edges out static at 4 workers** (1.58× vs 1.41×) because prime
  cost grows with value, so small chunks finish faster and free workers sooner.
  Static's rigid partitioning cannot exploit this. The effect is small at
  2 workers because each worker still gets a large enough sample that the cost
  averages out.

---

## 5. Metrics computed

| Metric               | Definition                                                                |
| -------------------- | ------------------------------------------------------------------------- |
| Wall time            | `time.perf_counter()` around each run                                     |
| Busy time per worker | Sum of per-chunk execution times, measured **inside** each worker process |
| Speedup              | `T_sequential / T_parallel`                                               |
| Efficiency           | `(Speedup / workers) × 100%`                                              |
| Load imbalance ratio | `(max_busy − min_busy) / mean_busy` per run                               |
| Correctness gate     | Parallel prime count must equal sequential count                          |

Worker identity is captured via `multiprocessing.current_process().pid` inside
the worker, so every per-worker statistic is tied to a real OS process — no
fabricated data.

---

## 6. Project layout

pdc_project/
├── core.py # prime check, process_chunk, run_static, run_dynamic
├── generate.py # builds data/input/numbers.npy
├── experiment.py # runs benchmarks, writes data/output/\*.csv
├── analysis.ipynb # loads CSVs, plots comparison charts
├── requirements.txt
├── README.md
└── data/
├── input/numbers.npy
└── output/{sequential,static,dynamic}\_results.csv

`core.py` has no side effects on import and contains only module-level worker
functions — required for Windows `spawn` compatibility.

---

## 7. How to reproduce

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

python generate.py         REM build the integer array
python experiment.py       REM run benchmarks -> data/output/*.csv
jupyter notebook           REM open analysis.ipynb, Run All
```

Requirements: numpy, pandas, matplotlib.

## 8. Notebook contents (maps to report sections)

Cell Chart / Output Report section it supports
1 Setup + sequential baseline printed Methodology
2 Equivalence assertion Correctness
3 Per-worker busy-time bar chart (static vs dynamic) Load balancing evidence
4 Load imbalance ratio table Quantitative scheduling comparison
5 Speedup vs worker count line chart Amdahl's Law / scaling ceiling
6 Parallel efficiency chart Diminishing returns narrative
7 Combined summary table Results table for the report

## 9. Key takeaways (for the report / presentation)

Correctness first. All three strategies (sequential, static, dynamic)
produced identical prime counts on the same input. Parallelism did not
corrupt the result.

Speedup is real but bounded. ~1.6× on 2 effective physical cores is
consistent with the hardware and the process-per-task model used.

Scheduling strategy matters when workloads are skewed. Prime-checking
cost grows with value, so rigid static partitioning leaves some workers
idle at the tail. Dynamic scheduling self-balances and is slightly faster
at higher worker counts.

More workers is not always better. Four workers regressed under static
scheduling because Windows spawn overhead and hyperthreading contention
outweighed the additional parallel capacity.

All measurements come from real process execution — real PIDs, real
per-chunk timings, real CSVs, real matplotlib output. No synthetic or
hard-coded benchmark values anywhere in the pipeline.

---

That README gives you: motivation, methodology, exact results table, honest interpretation, metrics definitions, reproduction steps, and a mapping from notebook cells to report sections. Every number in it is pulled directly from your actual `experiment.py` output.
