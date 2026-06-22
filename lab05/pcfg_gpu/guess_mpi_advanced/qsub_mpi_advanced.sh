#!/bin/sh
#PBS -N guess_advanced
#PBS -l walltime=01:00:00

PROJECT="/home/${USER}/guess_mpi_advanced"

NP=${NP:-2}
GENERATE=${GENERATE:-100000}
GEN_THREADS=${GEN_THREADS:-3}
BATCH_GUESSES=${BATCH_GUESSES:-10000}
BATCH_UNITS=${BATCH_UNITS:-64}

REMOTE_MAIN="/home/${USER}/guess_advanced_${PBS_JOBID%%.*}"
NODES=$(sort -u "$PBS_NODEFILE")
MPI_NODEFILE="/tmp/guess_advanced_nodes_${PBS_JOBID%%.*}"
ALLOCATED=$(wc -l < "$PBS_NODEFILE")

if [ "$NP" -gt "$ALLOCATED" ]; then
    echo "NP=$NP exceeds allocated slots=$ALLOCATED" >&2
    exit 2
fi

: > "$MPI_NODEFILE"
REMAINING=$NP
while [ "$REMAINING" -gt 0 ]; do
    for node in $NODES; do
        if [ "$REMAINING" -le 0 ]; then
            break
        fi
        echo "$node" >> "$MPI_NODEFILE"
        REMAINING=$((REMAINING - 1))
    done
done

echo "Version: advanced"
echo "PBS_JOBID: $PBS_JOBID"
echo "MPI processes: $NP"
echo "Generate count: $GENERATE"
echo "Generator threads: $GEN_THREADS"
echo "Batch guesses: $BATCH_GUESSES"
echo "Batch units: $BATCH_UNITS"
echo "Nodes:"
cat "$PBS_NODEFILE"
echo "MPI machinefile:"
cat "$MPI_NODEFILE"

for node in $NODES; do
    scp "master_ubss1:${PROJECT}/main" "${node}:${REMOTE_MAIN}" 1>&2
    ssh "$node" "chmod +x '${REMOTE_MAIN}'"
done

/usr/local/bin/mpiexec \
    -np "$NP" \
    -machinefile "$MPI_NODEFILE" \
    "$REMOTE_MAIN" \
    --generate "$GENERATE" \
    --gen-threads "$GEN_THREADS" \
    --batch-guesses "$BATCH_GUESSES" \
    --batch-units "$BATCH_UNITS"

STATUS=$?

for node in $NODES; do
    ssh "$node" "rm -f '${REMOTE_MAIN}'"
done
rm -f "$MPI_NODEFILE"

echo "Exit status: $STATUS"
exit "$STATUS"
