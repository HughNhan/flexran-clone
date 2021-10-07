#!/bin/sh

set -euo pipefail

source ./setting.env
source ./functions.sh

parse_args $@

echo "Removing PtpConfig ..."
oc delete -f ${MANIFEST_DIR}/ptp-config.yaml || true
echo "Removing PtpConfig: done"

echo "Restore chronyd.service ..."
oc delete -f ${MANIFEST_DIR}/disable-chronyd.yaml

if [[ "${WAIT_MCP}" == "true" ]]; then
    wait_mcp
fi

echo "Restore chronyd.service: done"

