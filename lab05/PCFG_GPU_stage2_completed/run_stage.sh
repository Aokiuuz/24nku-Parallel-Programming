#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${script_dir}/Makefile" ]]; then
  cd "${script_dir}"
else
  cd "${script_dir}/../.."
fi
mkdir -p results

date | tee results/stage2_environment.txt
hipcc --version | tee -a results/stage2_environment.txt
make clean
make gpu 2>&1 | tee results/stage2_build.log
./bin/pcfg_gpu_test --mode multi-check --pts 4 --batch 4096 \
  | tee results/stage2_correctness.txt
./bin/pcfg_gpu_test --mode multi-check --pts 2 --batch 1024 > /dev/null

{
  for run in 1 2 3 4 5; do
    echo "===== RUN ${run} ====="
    for pts in 2 4 8; do
      total=$((pts * 10000))
      ./bin/pcfg_gpu_test --mode bench --batch "$total"
      ./bin/pcfg_gpu_test --mode multi-bench --pts "$pts" --batch 10000
    done
  done
} | tee results/stage2_bench_5runs.txt

grep -E "^\[(bench|multi-bench)\]" results/stage2_bench_5runs.txt \
  > results/stage2_data_only.txt
echo "Stage 2 complete."
