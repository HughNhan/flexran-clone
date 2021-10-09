#!/bin/sh

set -euo pipefail

source ./setting.env
source ./functions.sh

mkdir -p ${MANIFEST_DIR}

OCP_CHANNEL=$(get_ocp_channel)

echo "install performance operator ..."
# skip if performance operator subscription already exists
if ! oc get Subscription performance-addon-operator -n openshift-performance-addon 2>/dev/null; then
    echo "generating ${MANIFEST_DIR}/sub-perf.yaml ..."
    envsubst < templates/sub-perf.yaml.template > ${MANIFEST_DIR}/sub-perf.yaml
    oc create -f ${MANIFEST_DIR}/sub-perf.yaml
    echo "generating ${MANIFEST_DIR}/sub-perf.yaml: done"
fi
wait_pod_in_namespace openshift-performance-addon
echo "install performance operator: done"

echo "install fec operator ..."
if ! oc get Subscription sriov-fec-subscription -n vran-acceleration-operators 2>/dev/null; then
    echo "generating ${MANIFEST_DIR}/sub-fec.yaml ..."
    envsubst < templates/sub-fec.yaml.template > ${MANIFEST_DIR}/sub-fec.yaml
    oc create -f ${MANIFEST_DIR}/sub-fec.yaml
    echo "generating ${MANIFEST_DIR}/sub-fec.yaml: done"
fi
wait_named_pod_in_namespace vran-acceleration-operators sriov-fec-controller-manager
echo "install fec operator: done"

echo "install ptp operator ..."
if ! oc get Subscription ptp-operator-subscription -n openshift-ptp 2>/dev/null; then
    echo "generating ${MANIFEST_DIR}/sub-ptp.yaml ..."
    envsubst < templates/sub-ptp.yaml.template > ${MANIFEST_DIR}/sub-ptp.yaml
    oc create -f ${MANIFEST_DIR}/sub-ptp.yaml
    echo "generating ${MANIFEST_DIR}/sub-ptp.yaml: done"
fi
wait_pod_in_namespace openshift-ptp
echo "install ptp operator: done"

echo "install sriov operator ..."
if ! oc get Subscription sriov-network-operator-subsription -n openshift-sriov-network-operator 2>/dev/null; then
    echo "generating ${MANIFEST_DIR}/sub-sriov.yaml ..."
    envsubst < templates/sub-sriov.yaml.template > ${MANIFEST_DIR}/sub-sriov.yaml
    oc create -f ${MANIFEST_DIR}/sub-sriov.yaml
    echo "generating ${MANIFEST_DIR}/sub-sriov.yaml: done"
fi
wait_pod_in_namespace openshift-sriov-network-operator
echo "install sriov operator: done"

