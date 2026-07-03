#!/bin/bash
set -euo pipefail
trap "echo 'Aborted'; exit 130" INT

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <num_iterations> <nth_iterations> <ingest|prepare|describe|model-rq12|model-rq3|posthoc-rq12|posthoc-rq3|significance-logging|tables|plots|all>"
    exit 1
fi

cd "$(dirname "$0")" || exit 1

NUM_ITER=$1
NTH_ITERS=$2
COMMAND=$3
OUTPUT_FOLDER="./results/$NUM_ITER-$NTH_ITERS"

if [ "$COMMAND" == "all" ]; then
    for subcmd in ingest prepare describe model-rq12 model-rq3 posthoc-rq12 posthoc-rq3 significance-logging tables plots; do
        echo "=== Running $subcmd ==="
        "$0" "$NUM_ITER" "$NTH_ITERS" "$subcmd"
    done
    exit 0
fi

mkdir -p "$OUTPUT_FOLDER/logs" "$OUTPUT_FOLDER/out"

log() { tee "$OUTPUT_FOLDER/logs/${1}.log"; }

case "$COMMAND" in
    ingest)
        python3 source/commands/ingest.py \
            2>&1 | log ingest
        ;;
    prepare)
        Rscript source/commands/prepare.r \
            benchmark_logs/raw.csv \
            "$NUM_ITER" "$NTH_ITERS" "$OUTPUT_FOLDER" \
            2>&1 | log prepare
        ;;
    describe)
        Rscript source/commands/describe.r \
            "$OUTPUT_FOLDER" \
            2>&1 | log describe
        ;;
    model-rq12)
        Rscript source/commands/model-rq12.r \
            "$OUTPUT_FOLDER" \
            2>&1 | log model-rq12
        ;;
    model-rq3)
        Rscript source/commands/model-rq3.r \
            "$OUTPUT_FOLDER" \
            2>&1 | log model-rq3
        ;;
    posthoc-rq12)
        Rscript source/commands/posthoc-rq12.r \
            "$OUTPUT_FOLDER" \
            2>&1 | log posthoc-rq12
        ;;
    posthoc-rq3)
        Rscript source/commands/posthoc-rq3.r \
            "$OUTPUT_FOLDER" \
            2>&1 | log posthoc-rq3
        ;;
    significance-logging)
        Rscript source/commands/significance-logging.r \
            "$OUTPUT_FOLDER" \
            2>&1 | log significance-logging
        ;;
    tables)
        python3 source/commands/tables.py \
            "$OUTPUT_FOLDER" \
            2>&1 | log tables
        ;;
    plots)
        python3 source/commands/plots.py \
            "$OUTPUT_FOLDER" \
            2>&1 | log plots
        ;;
    *)
        echo "Unknown command: $COMMAND"
        exit 1
        ;;
esac
