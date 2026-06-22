#!/bin/bash

set -u

ROOT="/home/${USER}"
BACKUP="${ROOT}/guess_mpi_backup"
BASE="${ROOT}/guess_mpi_base"
ADVANCED="${ROOT}/guess_mpi_advanced"

SUITE=${1:-formal}
RUNS=${RUNS:-3}
GENERATE=${GENERATE:-10000000}

mkdir -p "${BACKUP}/data" "${BASE}/data" "${ADVANCED}/data"

submit_backup() {
    TASK_ID=1
    MANIFEST="${BACKUP}/data/experiment_manifest.tsv"
    printf "task_id\tjob_id\tversion\tmode\trun\n" > "$MANIFEST"

    for MODE in simd serial; do
        for RUN in $(seq 1 "$RUNS"); do
            JOB_ID=$(qsub \
                -N "backup_${MODE}_${RUN}" \
                -l "nodes=1:ppn=1" \
                -o "${BACKUP}/data/mpi_task_${TASK_ID}.o" \
                -e "${BACKUP}/data/mpi_task_${TASK_ID}.e" \
                -v "MODE=${MODE}" \
                "${BACKUP}/qsub_mpi_backup.sh")

            printf "%s\t%s\tbackup\t%s\t%s\n" \
                "$TASK_ID" "$JOB_ID" "$MODE" "$RUN" >> "$MANIFEST"
            TASK_ID=$((TASK_ID + 1))
        done
    done
}

submit_base() {
    TASK_ID=1
    MANIFEST="${BASE}/data/experiment_manifest.tsv"
    printf "task_id\tjob_id\tversion\tnodes\tppn\tnp\tgenerate\trun\n" > "$MANIFEST"

    while read -r NODES PPN NP; do
        for RUN in $(seq 1 "$RUNS"); do
            JOB_ID=$(qsub \
                -N "base_np${NP}_${RUN}" \
                -l "nodes=${NODES}:ppn=${PPN}" \
                -o "${BASE}/data/mpi_task_${TASK_ID}.o" \
                -e "${BASE}/data/mpi_task_${TASK_ID}.e" \
                -v "NP=${NP},GENERATE=${GENERATE}" \
                "${BASE}/qsub_mpi_base.sh")

            printf "%s\t%s\tbase\t%s\t%s\t%s\t%s\t%s\n" \
                "$TASK_ID" "$JOB_ID" "$NODES" "$PPN" "$NP" "$GENERATE" "$RUN" >> "$MANIFEST"
            TASK_ID=$((TASK_ID + 1))
        done
    done <<EOF
1 1 1
1 2 2
1 4 4
1 8 8
2 8 16
4 8 32
EOF
}

submit_advanced_suite() {
    ADVANCED_SUITE="$1"
    TASK_ID=1
    MANIFEST="${ADVANCED}/data/experiment_manifest_${ADVANCED_SUITE}.tsv"
    printf "task_id\tjob_id\tversion\tsuite\tnodes\tppn\tnp\tgenerate\tgen_threads\tbatch_guesses\tbatch_units\trun\n" > "$MANIFEST"

    case "$ADVANCED_SUITE" in
        scale)
            CONFIGS="1 8 2 3 100000 64
1 8 4 3 100000 64
2 8 8 3 100000 64
4 8 16 3 100000 64"
            ;;
        threads)
            CONFIGS="1 8 4 1 100000 64
1 8 4 2 100000 64
1 8 4 3 100000 64
1 8 4 4 100000 64"
            ;;
        batch)
            CONFIGS="1 8 4 3 10000 64
1 8 4 3 50000 64
1 8 4 3 100000 64
1 8 4 3 500000 64"
            ;;
    esac

    while read -r NODES PPN NP GEN_THREADS BATCH_GUESSES BATCH_UNITS; do
        for RUN in $(seq 1 "$RUNS"); do
            JOB_ID=$(qsub \
                -N "advanced_${ADVANCED_SUITE}_${TASK_ID}" \
                -l "nodes=${NODES}:ppn=${PPN}" \
                -o "${ADVANCED}/data/${ADVANCED_SUITE}_mpi_task_${TASK_ID}.o" \
                -e "${ADVANCED}/data/${ADVANCED_SUITE}_mpi_task_${TASK_ID}.e" \
                -v "NP=${NP},GENERATE=${GENERATE},GEN_THREADS=${GEN_THREADS},BATCH_GUESSES=${BATCH_GUESSES},BATCH_UNITS=${BATCH_UNITS}" \
                "${ADVANCED}/qsub_mpi_advanced.sh")

            printf "%s\t%s\tadvanced\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
                "$TASK_ID" "$JOB_ID" "$ADVANCED_SUITE" "$NODES" "$PPN" "$NP" \
                "$GENERATE" "$GEN_THREADS" "$BATCH_GUESSES" "$BATCH_UNITS" "$RUN" >> "$MANIFEST"
            TASK_ID=$((TASK_ID + 1))
        done
    done <<< "$CONFIGS"
}

case "$SUITE" in
    backup)
        submit_backup
        ;;
    base)
        submit_base
        ;;
    advanced-scale)
        submit_advanced_suite scale
        ;;
    advanced-threads)
        submit_advanced_suite threads
        ;;
    advanced-batch)
        submit_advanced_suite batch
        ;;
    formal)
        submit_base
        submit_advanced_suite scale
        ;;
    all)
        submit_backup
        submit_base
        submit_advanced_suite scale
        submit_advanced_suite threads
        submit_advanced_suite batch
        ;;
    *)
        echo "Usage: $0 [backup|base|advanced-scale|advanced-threads|advanced-batch|formal|all]" >&2
        exit 2
        ;;
esac

qstat -u "$USER"
