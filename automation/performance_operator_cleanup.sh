#!/bin/sh

set -euo pipefail

source ./setting.env
source ./functions.sh

echo "Removing performance profile ..."
oc delete -f ${MANIFEST_DIR}/performance_profile.yaml

sleep 30
status=$(get_mcp_progress_status)
count=100
while [[ $status != "False" ]]; do
    if ((count == 0)); then
        echo "timeout waiting for performance profile complete on the baremetal host!"
        exit 1
    fi
    count=$((count-1))
    echo "waiting for performance profile complete on the baremetal host ..."
    sleep 5
    status=$(get_mcp_progress_status)
done

echo "Removing performance profile: done"

