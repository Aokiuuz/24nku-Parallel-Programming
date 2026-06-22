#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[build] building pcfg test binary"
make gpu

echo "[run] cpu baseline"
./bin/pcfg_gpu_test --mode cpu --batch 1024
./bin/pcfg_gpu_test --mode cpu --batch 10000
./bin/pcfg_gpu_test --mode cpu --batch 100000
