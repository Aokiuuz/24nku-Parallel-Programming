#!/bin/sh
#PBS -N guess_backup
#PBS -l walltime=01:00:00

PROJECT="/home/${USER}/guess_mpi_backup"

MODE=${MODE:-simd}

REMOTE_MAIN="/home/${USER}/guess_backup_${PBS_JOBID%%.*}"
NODES=$(sort -u "$PBS_NODEFILE")

echo "Version: backup"
echo "PBS_JOBID: $PBS_JOBID"
echo "Hash mode: $MODE"
echo "Generate count: 10000000"
echo "Nodes:"
cat "$PBS_NODEFILE"

for node in $NODES; do
    scp "master_ubss1:${PROJECT}/main" "${node}:${REMOTE_MAIN}" 1>&2
    ssh "$node" "chmod +x '${REMOTE_MAIN}'"
done

if [ "$MODE" = "serial" ]; then
    "$REMOTE_MAIN" --serial
else
    "$REMOTE_MAIN"
fi

STATUS=$?

for node in $NODES; do
    ssh "$node" "rm -f '${REMOTE_MAIN}'"
done

echo "Exit status: $STATUS"
exit "$STATUS"
