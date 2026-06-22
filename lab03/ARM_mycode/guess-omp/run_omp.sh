#!/bin/sh
set -eu

cd "$(dirname "$0")"

VERSION=OMP
RUNS=${1:-1}
OPT_LEVELS=${OPT_LEVELS:-"O0 O1 O2"}
THREAD_LIST=${THREAD_LIST:-"1 2 4 8 16"}
OUTPUT_DIR=${OUTPUT_DIR:-data}
RESULTS=${OUTPUT_DIR}/results.csv
SUMMARY=${OUTPUT_DIR}/summary.csv

if [ ! -d "$OUTPUT_DIR" ]; then
    echo "Output directory not found: ${OUTPUT_DIR}" >&2
    echo "Create it first, for example: mkdir ${OUTPUT_DIR}" >&2
    exit 1
fi

if [ ! -f "$RESULTS" ]; then
    echo "version,opt,threads,run,guess_time,hash_time,train_time,total_time,status,output_file" > "$RESULTS"
fi

compile_main() {
    opt=$1
    g++ main.cpp train.cpp guessing.cpp md5.cpp "-${opt}" -fopenmp -o main
}

wait_for_job() {
    job_id=$1
    while qstat "$job_id" >/dev/null 2>&1; do
        sleep 5
    done
}

wait_for_output() {
    tries=0
    while [ ! -s test.o ] && [ "$tries" -lt 60 ]; do
        tries=$((tries + 1))
        sleep 1
    done
}

extract_metric() {
    label=$1
    file=$2
    sed -n "s/.*${label}:\([0-9.]*\)seconds.*/\1/p" "$file" | tail -n 1
}

append_result() {
    opt=$1
    threads=$2
    run=$3
    outfile=$4

    guess=$(extract_metric "Guess time" "$outfile")
    hash_time=$(extract_metric "Hash time" "$outfile")
    train=$(extract_metric "Train time" "$outfile")
    status=ok
    total=

    if [ -z "$guess" ] || [ -z "$hash_time" ] || [ -z "$train" ]; then
        status=missing_metrics
    else
        total=$(awk -v g="$guess" -v h="$hash_time" 'BEGIN { printf "%.6f", g + h }')
    fi

    echo "${VERSION},${opt},${threads},${run},${guess},${hash_time},${train},${total},${status},${outfile}" >> "$RESULTS"
}

write_summary() {
    awk -F, '
        NR == 1 { next }
        $9 == "ok" {
            key = $1 SUBSEP $2 SUBSEP $3
            count[key] += 1
            guess[key] += $5
            hash_time[key] += $6
            train[key] += $7
            total[key] += $8
        }
        END {
            print "version,opt,threads,runs,avg_guess,avg_hash,avg_train,avg_total"
            for (key in count) {
                split(key, parts, SUBSEP)
                printf "%s,%s,%s,%d,%.6f,%.6f,%.6f,%.6f\n", parts[1], parts[2], parts[3], count[key], guess[key] / count[key], hash_time[key] / count[key], train[key] / count[key], total[key] / count[key]
            }
        }
    ' "$RESULTS" > "$SUMMARY"
}

run_once() {
    opt=$1
    threads=$2
    run=$3

    rm -f test.o test.e
    job_id=$(qsub -v OMP_NUM_THREADS="$threads" qsub.sh)
    wait_for_job "$job_id"
    wait_for_output

    stamp=$(date +%Y%m%d-%H%M)
    stem="${stamp}_${VERSION}_${opt}_T${threads}_run${run}"
    outfile="${OUTPUT_DIR}/${stem}.o"
    errfile="${OUTPUT_DIR}/${stem}.e"

    cp test.o "$outfile"
    if [ -f test.e ]; then
        cp test.e "$errfile"
    fi

    append_result "$opt" "$threads" "$run" "$outfile"
    write_summary
}

for opt in $OPT_LEVELS; do
    echo "== ${VERSION} ${opt}: compiling =="
    compile_main "$opt"
    for threads in $THREAD_LIST; do
        run=1
        while [ "$run" -le "$RUNS" ]; do
            echo "== ${VERSION} ${opt} T${threads} run ${run}/${RUNS} =="
            run_once "$opt" "$threads" "$run"
            run=$((run + 1))
        done
    done
done

echo "Results: ${RESULTS}"
echo "Summary: ${SUMMARY}"
