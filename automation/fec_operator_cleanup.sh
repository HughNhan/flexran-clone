#!/bin/sh

set -euo pipefail

source ./setting.env
source ./functions.sh

parse_args $@

echo "Removing acc100 VF ..."
oc delete -f ${MANIFEST_DIR}/create-vf-acc100.yaml
echo "Removing acc100 VF: done"

if [[ "${WAIT_MCP}" == "true" ]]; then
    wait_mcp
fi

