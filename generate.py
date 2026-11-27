"""
Generates the integer array and saves it to data/input/numbers.npy.
Run: python generate.py
"""

import os
import numpy as np

M = 1_000_000          # scan integers in [1, M]
SHUFFLE = True         # True = balanced cost order; False = sorted (heavy skew)
SEED = 42

OUT_DIR = os.path.join("data", "input")
OUT_PATH = os.path.join(OUT_DIR, "numbers.npy")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    arr = np.arange(1, M + 1, dtype=np.int64)

    if SHUFFLE:
        rng = np.random.default_rng(SEED)
        rng.shuffle(arr)   # in-place
        tag = "shuffled (balanced)"
    else:
        tag = "sorted (skewed: small->large)"

    np.save(OUT_PATH, arr)
    print(f"[generate] M={M:,}  order={tag}")
    print(f"[generate] saved -> {OUT_PATH}  ({arr.nbytes / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()