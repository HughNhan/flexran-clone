#!/bin/sh

set -euo pipefail

source ./setting.env
source ./functions.sh

parse_args $@

if oc get deploy flexran-du 2>/dev/null; then
    oc delete --wait=false deploy flexran-du
fi

printf "deleting pod from deployment flexran-du" 
if [[ "${WAIT_MCP}" == "true" ]]; then
    count=30
    while oc get pod 2>/dev/null | grep flexran-du 1>/dev/null; do
       count=$((count -1))
       if ((count == 0)); then
           printf "\nfailed to delete pod from deployment flexran-du!\n"
           exit 1
       fi
       printf "."
       sleep 5
    done
    printf "\ndeployment flexran-du deleted\n"
fi

