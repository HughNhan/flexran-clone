#!/bin/sh

set -euo pipefail

source ./setting.env
source ./functions.sh

parse_args $@

echo "deleting pod flexran-du ..."
if oc get pod flexran-du 2>/dev/null; then
    oc delete --wait=false pod flexran-du
fi

if [[ "${WAIT_MCP}" == "true" ]]; then
    count=30
    while oc get pod flexran-du 2>/dev/null; do
       count=$((count -1))
       if ((count == 0)); then
           echo "pod flexran-du still up!"
           exit 1
       fi
       echo "waiting for pod flexran-du delete ..."
       sleep 5
    done
    echo "deleting pod flexran-du: done"
fi

