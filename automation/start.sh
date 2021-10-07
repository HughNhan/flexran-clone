#/bin/sh

set -euo pipefail

source ./setting.env
source ./functions.sh

echo "setup du ..."
./performance_operator_install.sh -n
# uncomment this after fec operator bug fixed
#./fec_operator_install.sh -n
./ptp_operator_install.sh -n
./sriov_operator_install.sh -n
wait_mcp

# remove below line after fec operator bug fixed
./fec_operator_install.sh

echo "setup ru ..."
./ru_sriov.sh setup
./ru_ptp.sh setup
./ru_start.sh

##### now run the pod test ####
./du_pod_install.sh

