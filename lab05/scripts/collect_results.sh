#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p results
out="results/gpu_bench_raw.txt"

make gpu
{
  echo "# Raw pcfg_gpu_test output. Fill result_template.csv manually after checking correctness."
  ./bin/pcfg_gpu_test --mode check --batch 1024
  ./bin/pcfg_gpu_test --mode multi-check --pts 4 --batch 4096
  ./bin/pcfg_gpu_test --mode overlap-check --pts 4 --batch 4096
  ./bin/pcfg_gpu_test --mode schedule
  ./bin/pcfg_gpu_test --mode bench --batch 1024
  ./bin/pcfg_gpu_test --mode bench --batch 10000
  ./bin/pcfg_gpu_test --mode bench --batch 100000
  ./bin/pcfg_gpu_test --mode multi-bench --pts 4 --batch 10000
  ./bin/pcfg_gpu_test --mode overlap-bench --pts 4 --batch 10000
  ./bin/pcfg_gpu_test --mode schedule-bench
} | tee "$out"
