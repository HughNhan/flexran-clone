#!/bin/sh

set -euo pipefail

source ./setting.env
source ./functions.sh

parse_args $@

if oc get pod flexran-du 2>/dev/null; then
    oc delete --wait=false pod flexran-du
fi

printf "deleting pod flexran-du" 
if [[ "${WAIT_MCP}" == "true" ]]; then
    count=30
    while oc get pod flexran-du 1>/dev/null 2>&1; do
       count=$((count -1))
       if ((count == 0)); then
           printf "\nfailed to delete pod flexran-du!\n"
           exit 1
       fi
       printf "."
       sleep 5
    done
    printf "\npod flexran-du deleted\n"
fi

#delete name space
#oc delete namespace flexran-test

