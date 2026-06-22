#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[env] hipcc version"
hipcc --version

echo "[build] building gpu pcfg"
make clean || true
make gpu

echo "[run] correctness test"
./bin/pcfg_gpu_test --mode check --batch 1024
./bin/pcfg_gpu_test --mode multi-check --pts 4 --batch 4096
./bin/pcfg_gpu_test --mode overlap-check --pts 4 --batch 4096
./bin/pcfg_gpu_test --mode schedule

echo "[run] performance template"
./bin/pcfg_gpu_test --mode bench --batch 1024
./bin/pcfg_gpu_test --mode bench --batch 10000
./bin/pcfg_gpu_test --mode bench --batch 100000
./bin/pcfg_gpu_test --mode multi-bench --pts 4 --batch 10000
./bin/pcfg_gpu_test --mode overlap-bench --pts 4 --batch 10000
./bin/pcfg_gpu_test --mode schedule-bench
