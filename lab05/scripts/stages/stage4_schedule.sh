#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${script_dir}/Makefile" ]]; then
  cd "${script_dir}"
else
  cd "${script_dir}/../.."
fi
mkdir -p results

date | tee results/stage4_environment.txt
hipcc --version | tee -a results/stage4_environment.txt
make clean
make gpu 2>&1 | tee results/stage4_build.log
./bin/pcfg_gpu_test --mode schedule \
  | tee results/stage4_correctness.txt
./bin/pcfg_gpu_test --mode schedule > /dev/null

{
  for run in 1 2 3 4 5; do
    echo "===== RUN ${run} ====="
    ./bin/pcfg_gpu_test --mode schedule-bench
  done
} | tee results/stage4_bench_5runs.txt

grep -E "^\[schedule-bench\]" results/stage4_bench_5runs.txt \
  > results/stage4_data_only.txt
echo "Stage 4 complete."
