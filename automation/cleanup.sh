#!/usr/bin/bash
set -eu

source ./setting.env
source ./functions.sh

echo "clean up ru ..."
./ru_stop.sh
./ru_ptp.sh clean
./ru_sriov.sh clean

echo "clean up du ..."
./du_pod_cleanup.sh
./sriov_operator_cleanup.sh -n
./ptp_operator_cleanup.sh -n
./fec_operator_cleanup.sh -n
./performance_operator_cleanup.sh -n

wait_mcp

echo "clean up: complete"
