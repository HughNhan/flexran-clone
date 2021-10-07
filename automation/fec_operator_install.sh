#!/bin/sh

set -euo pipefail

source ./setting.env
source ./functions.sh

parse_args $@

oc label --overwrite node ${BAREMETAL_WORKER} fpga.intel.com/intel-accelerator-present="" 

# skip if fec operator subscription already exists 
if ! oc get Subscription sriov-fec-subscription -n vran-acceleration-operators 2>/dev/null; then 
    echo "generating ${MANIFEST_DIR}/sub-fec.yaml ..."
    envsubst < templates/sub-fec.yaml.template > ${MANIFEST_DIR}/sub-fec.yaml
    oc create -f ${MANIFEST_DIR}/sub-fec.yaml
    echo "generating ${MANIFEST_DIR}/sub-fec.yaml: done"
fi

wait_named_pod_in_namespace vran-acceleration-operators sriov-fec-controller-manager

echo "generating ${MANIFEST_DIR}/create-vf-acc100.yaml ..."
mkdir -p ${MANIFEST_DIR}/
envsubst < templates/create-vf-acc100.yaml.template > ${MANIFEST_DIR}/create-vf-acc100.yaml
echo "generating ${MANIFEST_DIR}/create-vf-acc100.yaml: done"

# workaround for fec operator bug
oc delete SriovFecClusterConfig config -n vran-acceleration-operators 2>/dev/null || true

if ! oc get SriovFecClusterConfig config -n vran-acceleration-operators 2>/dev/null; then
    echo "create SriovFecClusterConfig ..."
    oc create -f ${MANIFEST_DIR}/create-vf-acc100.yaml
    echo "create SriovFecClusterConfig: done"
fi

if [[ "${WAIT_MCP}" == "true" ]]; then
    wait_mcp
fi

echo "create FEC VF: done"
