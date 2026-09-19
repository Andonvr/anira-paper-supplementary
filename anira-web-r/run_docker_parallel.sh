#!/bin/bash
# Runs the whole pipeline inside the Docker image, fitting the RQ1/RQ2 and RQ3
# chains in parallel (they are independent after `prepare`).
set -euo pipefail
trap "echo 'Aborted'; kill 0; exit 130" INT

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    echo "Usage: $0 <num_iterations> <nth_iterations> [docker_image]"
    exit 1
fi

cd "$(dirname "$0")" || exit 1

NUM_ITER=$1
NTH_ITERS=$2
IMAGE=${3:-anira-r}
# BLAS threads per chain; two chains run concurrently, so keep 2x this <= core count
BLAS_THREADS=${BLAS_THREADS:-16}

run_step() {
    echo "=== Running $1 ==="
    docker run --rm \
        -e OPENBLAS_NUM_THREADS="$BLAS_THREADS" \
        -v "$PWD":/home/ -w /home/ \
        "$IMAGE" ./run_advanced.sh "$NUM_ITER" "$NTH_ITERS" "$1"
    echo "=== Finished $1 ($(date '+%F %T')) ==="
}

run_chain() {
    for subcmd in "$@"; do
        run_step "$subcmd"
    done
}

START=$(date +%s)

run_chain ingest prepare describe tails

run_chain model-rq12 posthoc-rq12 &
PID_RQ12=$!
run_chain model-rq3 posthoc-rq3 &
PID_RQ3=$!

# `wait <pid>` returns the chain's exit status, so a failed chain aborts the script
FAILED=0
wait "$PID_RQ12" || { echo "RQ1/RQ2 chain failed"; FAILED=1; }
wait "$PID_RQ3"  || { echo "RQ3 chain failed"; FAILED=1; }
[ "$FAILED" -eq 0 ] || exit 1

run_chain significance-logging tables plots

echo "All done in $(( ($(date +%s) - START) / 60 )) minutes."
