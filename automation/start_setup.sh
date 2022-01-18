#/bin/sh

set -euo pipefail

####Following line is for dci debug @80
#cp -R pod/cfg_examples/setting_timermode_only.env setting.env
#### End of dci debug @80

source ./setting.env
source ./functions.sh

echo "prepare host ..."
./host_prep.sh

./create_mcp.sh

pause_mcp
echo "setup du for timer mode test ..."
./performance_operator_install.sh -n
./fec_operator_install.sh -n

echo "wait mcp to complete ..."
wait_mcp

#create flexran test namespace
if ! oc get namespace ${FLEXRAN_DU_NS} 2>/dev/null; then
    echo "Create namespace ${FLEXRAN_DU_NS}"
    oc create namespace ${FLEXRAN_DU_NS}
fi

exit 0
