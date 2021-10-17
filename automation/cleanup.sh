#!/usr/bin/bash
set -eu

source ./setting.env
source ./functions.sh

if [[ "${RUN_XRAN}" == "true" ]]; then
    echo "clean up ru ..."
    ./ru_stop.sh
    ./ru_ptp.sh clean
    ./ru_sriov.sh clean
fi

echo "clean up du ..."
./du_pod_cleanup.sh

pause_mcp
if [[ "${RUN_XRAN}" == "true" ]]; then
    ./sriov_operator_cleanup.sh -n
    ./ptp_operator_cleanup.sh -n
fi

if [[ "${DU_FEC}" != "SW" ]]; then
    ./fec_operator_cleanup.sh -n
fi

./performance_operator_cleanup.sh -n

wait_mcp

echo "clean up: complete"
