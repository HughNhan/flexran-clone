#/bin/sh

set -euo pipefail

source ./setting.env
source ./functions.sh

echo "prepare host ..."
./host_prep.sh

echo "install operators ..."
./install_operators.sh

echo "setup du for timer mode test ..."
./performance_operator_install.sh -n
# uncomment this after fec operator bug fixed
#./fec_operator_install.sh -n

echo "wait mcp to complete ..."
wait_mcp

# remove below line after fec operator bug fixed
./fec_operator_install.sh

##### now run the timer mode test suites ####
./du_pod_install.sh

if [[ "${RUN_XRAN:-false}" == "false" ]]; then
    echo "test complete"
    exit 0
fi

#### the following is prepare for front haul test ####
./du_pod_cleanup.sh

./ptp_operator_install.sh -n
./sriov_operator_install.sh -n

echo "wait mcp to complete ..."
wait_mcp

# remove below line after fec operator bug fixed
./fec_operator_install.sh

echo "setup ru ..."
./ru_sriov.sh setup
./ru_ptp.sh setup
./ru_start.sh

##### now run the front haul test ####
./du_pod_install.sh -x

echo "test complete"
exit 0
