#!/bin/sh

set -euo pipefail

source ./setting.env
source ./functions.sh

if ! oc get mcp worker-cnf 2>/dev/null; then
    echo "create mcp for worker-cnf ..."
    envsubst < templates/mcp-worker-cnf.yaml.template > ${MANIFEST_DIR}/mcp-worker-cnf.yaml
    oc create -f ${MANIFEST_DIR}/mcp-worker-cnf.yaml
    echo "create mcp for worker-cnf: done"
fi

