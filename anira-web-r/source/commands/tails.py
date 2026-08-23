"""Tail statistics of the per-block runtimes.

Descriptive, not model-based: for every benchmark configuration this computes
the spread (SD), the 99th percentile, the maximum, and the deadline-miss rate
of the raw per-iteration measurements, once over all iterations and once over
the steady state (iteration >= 1, i.e. excluding the cold-start iteration of
every repetition that RQ2 examines separately).

A deadline miss is a block whose runtime exceeds the duration of the audio it
carries, i.e. Runtime > Buffer Size / sample rate, equivalently RpS > RTT.

Reads benchmark_logs/raw.csv with the same iteration filter as prepare.r and
writes <results_dir>/tails.csv. Runtimes in the CSV are ms/sample, matching
describe.csv; tables.py converts to µs/sample for the paper.
"""

import csv
import math
import os
import statistics
import sys
from collections import defaultdict

SAMPLE_RATE = 44100.0

MODEL_UNIQUE = {
    "steerable-nafx-libtorch-dynamic.onnx": "steerable-nafx",
    "GuitarLSTM-libtorch-dynamic.onnx": "guitar-lstm",
}

# Same run -> backend / pre-post-processor mapping as prepare.r.
BACKEND_MAP = {
    "bypass": "wasm-bypass",
    "onnx": "wasm-onnx",
    "js-bypass": "js-bypass",
    "onnxrt-web": "js-onnx",
    "bypass-jspp": "wasm-bypass",
    "onnx-jspp": "wasm-onnx",
    "js-bypass-jspp": "js-bypass",
    "onnxrt-web-jspp": "js-onnx",
}
PP_MAP = {run: ("js" if run.endswith("-jspp") else "wasm") for run in BACKEND_MAP}


def percentile(values: list[float], p: float) -> float:
    """Linear-interpolated percentile (type 7, as R's quantile() default)."""
    xs = sorted(values)
    k = (len(xs) - 1) * p
    lo = math.floor(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def summarise(rows: list[tuple[int, float]], buffer_size: int) -> dict:
    """rows: (iteration, runtime_ms). Returns stats in ms/sample and miss rates."""
    budget_ms = buffer_size / SAMPLE_RATE * 1e3

    def stats(runtimes: list[float], suffix: str) -> dict:
        per_sample = [r / buffer_size for r in runtimes]
        return {
            f"N{suffix}": len(runtimes),
            f"Mean{suffix}": statistics.fmean(per_sample),
            f"SD{suffix}": statistics.stdev(per_sample),
            f"P99{suffix}": percentile(per_sample, 0.99),
            f"Max{suffix}": max(per_sample),
            f"Miss{suffix}": sum(r > budget_ms for r in runtimes) / len(runtimes),
        }

    all_runtimes = [r for _, r in rows]
    steady_runtimes = [r for it, r in rows if it >= 1]
    return {**stats(all_runtimes, ""), **stats(steady_runtimes, "_Steady")}


def main() -> None:
    if len(sys.argv) != 5:
        sys.exit("Usage: tails.py <csv_file> <max_iterations> <nth_iteration> <results_dir>")
    csv_file, max_iterations, nth_iteration, results_dir = (
        sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    os.makedirs(results_dir, exist_ok=True)

    groups: dict[tuple, list[tuple[int, float]]] = defaultdict(list)
    with open(csv_file, newline="") as f:
        for row in csv.DictReader(f):
            iteration = int(row["Iteration Count"])
            if iteration % nth_iteration != 0 or iteration > max_iterations:
                continue
            key = (row["Environment"], MODEL_UNIQUE[row["Model"]], row["Run"],
                   int(row["Buffer Size"]))
            groups[key].append((iteration, float(row["Runtime"])))

    out_rows = []
    for (env, model, run, buffer_size), rows in sorted(groups.items()):
        out_rows.append({
            "Environment": env,
            "Model": model,
            "Run": run,
            "Backend": BACKEND_MAP[run],
            "PP": PP_MAP[run],
            "Buffer.Size": buffer_size,
            **summarise(rows, buffer_size),
        })

    out_path = os.path.join(results_dir, "tails.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"tails.csv written to {results_dir} ({len(out_rows)} configurations)")


if __name__ == "__main__":
    main()
