#!/bin/sh
#PBS -N guess_base
#PBS -l walltime=01:00:00

PROJECT="/home/${USER}/guess_mpi_base"

NP=${NP:-2}
GENERATE=${GENERATE:-100000}

REMOTE_MAIN="/home/${USER}/guess_base_${PBS_JOBID%%.*}"
NODES=$(sort -u "$PBS_NODEFILE")

echo "Version: base"
echo "PBS_JOBID: $PBS_JOBID"
echo "MPI processes: $NP"
echo "Generate count: $GENERATE"
echo "Nodes:"
cat "$PBS_NODEFILE"

for node in $NODES; do
    scp "master_ubss1:${PROJECT}/main" "${node}:${REMOTE_MAIN}" 1>&2
    ssh "$node" "chmod +x '${REMOTE_MAIN}'"
done

/usr/local/bin/mpiexec \
    -np "$NP" \
    -machinefile "$PBS_NODEFILE" \
    "$REMOTE_MAIN" \
    --generate "$GENERATE"

STATUS=$?

for node in $NODES; do
    ssh "$node" "rm -f '${REMOTE_MAIN}'"
done

echo "Exit status: $STATUS"
exit "$STATUS"
