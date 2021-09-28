#!/usr/bash
set -eu

./ru_stop.sh
./ru_ptp.sh clean
./ru_sriov.sh clean
