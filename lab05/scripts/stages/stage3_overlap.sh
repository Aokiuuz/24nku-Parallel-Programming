#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${script_dir}/Makefile" ]]; then
  cd "${script_dir}"
else
  cd "${script_dir}/../.."
fi
mkdir -p results

date | tee results/stage3_environment.txt
hipcc --version | tee -a results/stage3_environment.txt
make clean
make gpu 2>&1 | tee results/stage3_build.log
./bin/pcfg_gpu_test --mode overlap-check --pts 4 --batch 4096 \
  | tee results/stage3_correctness.txt
./bin/pcfg_gpu_test --mode overlap-check --pts 2 --batch 1024 > /dev/null

{
  for run in 1 2 3 4 5; do
    echo "===== RUN ${run} ====="
    for pts in 2 4 8; do
      ./bin/pcfg_gpu_test --mode multi-bench --pts "$pts" --batch 10000
      ./bin/pcfg_gpu_test --mode overlap-bench --pts "$pts" --batch 10000
    done
  done
} | tee results/stage3_bench_5runs.txt

grep -E "^\[(multi-bench|overlap-bench)\]" results/stage3_bench_5runs.txt \
  > results/stage3_data_only.txt
echo "Stage 3 complete."
