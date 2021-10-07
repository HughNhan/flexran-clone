#!/bin/sh

set -euo pipefail

source ./setting.env
source ./functions.sh

set_registry

if ! oc get pod flexran-du 2>/dev/null; then
    echo "generating ${MANIFEST_DIR}/pod_flexran_acc100.yaml ..."
    export FLEXRAN_VERSION=$(basename ${FLEXRAN_DIR}/SDK*.sh | sed -n -r 's/SDK-([0-9.]+)\.sh/\1/p')
    envsubst < templates/pod_flexran_acc100.yaml.template > ${MANIFEST_DIR}/pod_flexran_acc100.yaml
    oc create -f ${MANIFEST_DIR}/pod_flexran_acc100.yaml
    echo "generating ${MANIFEST_DIR}/pod_flexran_acc100.yaml: done"
fi

wait_named_pod_in_namespace default flexran-du

