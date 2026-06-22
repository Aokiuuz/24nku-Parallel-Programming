#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root_dir="$(cd "${script_dir}/.." && pwd)"
cd "${root_dir}"
mkdir -p results

trap 'echo "[error] run_real_pcfg.sh stopped at line ${LINENO}" >&2' ERR

if [[ -n "${TRAIN_PATH:-}" ]]; then
  train_path="${TRAIN_PATH}"
elif [[ -r /guessdata/Rockyou-singleLined-full.txt ]]; then
  train_path="/guessdata/Rockyou-singleLined-full.txt"
elif [[ -r data/Rockyou-1m.txt ]]; then
  train_path="data/Rockyou-1m.txt"
else
  echo "[error] No readable PCFG training data was found." >&2
  echo "Set TRAIN_PATH, use /guessdata/Rockyou-singleLined-full.txt, or upload data/Rockyou-1m.txt." >&2
  exit 2
fi

{
  echo "utc_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "host=$(hostname)"
  echo "working_directory=${root_dir}"
  echo "train_path=${train_path}"
  echo "dataset_lines=$(wc -l < "${train_path}")"
  echo "dataset_bytes=$(wc -c < "${train_path}")"
  if command -v sha256sum >/dev/null 2>&1; then
    echo "dataset_sha256=$(sha256sum "${train_path}" | awk '{print $1}')"
  fi
  echo "uname=$(uname -a)"
  hipcc --version
  if command -v rocminfo >/dev/null 2>&1; then
    rocminfo | grep -E "Marketing Name:|Compute Unit:|Wavefront Size:" | head -n 20 || true
  fi
} | tee results/real_environment.txt

make clean
make gpu real-pcfg 2>&1 | tee results/real_build.log

{
  ./bin/pcfg_gpu_test --mode check --batch 1024
  ./bin/pcfg_gpu_test --mode multi-check --pts 4 --batch 4096
  ./bin/pcfg_gpu_test --mode overlap-check --pts 4 --batch 4096
  ./bin/pcfg_gpu_test --mode schedule
} | tee results/real_synthetic_regression.txt

./bin/pcfg_real_gpu_test \
  --train "${train_path}" \
  --limits 10000,100000,1000000 \
  --repeats 5 \
  --pts-per-batch 4 \
  | tee results/real_raw.txt

python3 scripts/analyze_real_results.py \
  results/real_raw.txt --output-dir results
if python3 -c 'import matplotlib, pandas, seaborn' >/dev/null 2>&1; then
  if ! python3 scripts/plot_real_results.py --results-dir results; then
    echo "[warning] Figure generation failed; validated CSV files were still produced."
  fi
else
  echo "[warning] matplotlib/pandas/seaborn unavailable; validated CSV files were still produced."
fi

echo "Real PCFG experiment complete."
echo "Validation: results/real_validation.txt"
