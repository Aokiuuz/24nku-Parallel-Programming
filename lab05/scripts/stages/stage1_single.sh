#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${script_dir}/Makefile" ]]; then
  cd "${script_dir}"
else
  cd "${script_dir}/../.."
fi
mkdir -p results

date | tee results/stage1_environment.txt
hipcc --version | tee -a results/stage1_environment.txt
rocminfo | grep -E "Marketing Name|Compute Unit|Wavefront Size" \
  | tee -a results/stage1_environment.txt

make clean
make gpu 2>&1 | tee results/stage1_build.log
./bin/pcfg_gpu_test --mode check --batch 1024 \
  | tee results/stage1_correctness.txt
./bin/pcfg_gpu_test --mode check --batch 1024 > /dev/null

{
  for run in 1 2 3 4 5; do
    echo "===== RUN ${run} ====="
    for batch in 1024 10000 100000; do
      ./bin/pcfg_gpu_test --mode cpu --batch "$batch"
      ./bin/pcfg_gpu_test --mode bench --batch "$batch"
    done
  done
} | tee results/stage1_bench_5runs.txt

grep -E "^\[(cpu|bench)\]" results/stage1_bench_5runs.txt \
  > results/stage1_data_only.txt
echo "Stage 1 complete."
