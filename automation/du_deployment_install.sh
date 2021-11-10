#!/bin/sh

set -euo pipefail

source ./setting.env
source ./functions.sh

parse_args() {
   USAGE="Usage: $0 [options]
Options:
    -x             Setup deployment for front haul test
    -h             This.

This script starts a flexran deployment. 
"
    while getopts "xh" OPTION
    do
        case $OPTION in
            x) timer_mode="false" ;;
            h) echo "$USAGE"; exit;;
            *) echo "$USAGE"; exit 1;;
        esac
    done
}

parse_args $@

if ! oc get deploy flexran-du 2>/dev/null; then
    echo "generating ${MANIFEST_DIR}/deployment_flexran.yaml ..."
    # is there a local flexran install?
    local_install_version=$(basename ${FLEXRAN_DIR}/SDK*.sh | sed -n -r 's/SDK-([0-9.]+)\.sh/\1/p')
    export FLEXRAN_VERSION=${FLEXRAN_VERSION:-${local_install_version}}
    if [[ -z "${FLEXRAN_VERSION}" ]]; then
        echo "couldn't find env FLEXRAN_VERSION!"
        exit 1
    fi
    envsubst < templates/deployment_flexran.yaml.template > ${MANIFEST_DIR}/deployment_flexran.yaml
    if [[ "${DU_FEC}" == "SW" ]]; then
        # remove intel.com/intel_fec_acc100: line
        sed -i '/intel.com\/intel_fec_acc100:/d' ${MANIFEST_DIR}/deployment_flexran.yaml
    elif [[ "${DU_FEC}" == "N3000" ]]; then
        # replace with intel.com/intel_fec_5g
        sed -i 's/intel_fec_acc100:/intel_fec_5g:/g' ${MANIFEST_DIR}/deployment_flexran.yaml
    elif [[ "${DU_FEC}" == "ACC100" ]]; then
        :
    else
        echo "invalid env DU_FEC: ${DU_FEC}"
        exit 1
    fi 
    echo "generating ${MANIFEST_DIR}/deployment_flexran.yaml: done"

    if [[ "${timer_mode:-true}" == "true" ]]; then
        yq -i -y 'del(.spec.template.metadata.annotations)' ${MANIFEST_DIR}/deployment_flexran.yaml
    fi

    oc create -f ${MANIFEST_DIR}/deployment_flexran.yaml
fi

wait_named_pod_in_namespace default flexran-du
