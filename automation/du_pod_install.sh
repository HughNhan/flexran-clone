#!/bin/sh

set -euo pipefail

source ./setting.env
source ./functions.sh

parse_args() {
   USAGE="Usage: $0 [options]
Options:
    -x             Setup pod for front haul test
    -h             This.

This script starts a flexran test pod. 
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

if ! oc get pod flexran-du --namespace ${FLAXRAN_TEST_NS} 2>/dev/null; then
    echo "generating ${MANIFEST_DIR}/pod_flexran_du.yaml ..."
    # is there a local flexran install?
    local_install_version=$(basename ${FLEXRAN_DIR}/SDK*.sh | sed -n -r 's/SDK-([0-9.]+)\.sh/\1/p')
    export FLEXRAN_VERSION=${FLEXRAN_VERSION:-${local_install_version}}
    if [[ -z "${FLEXRAN_VERSION}" ]]; then
        echo "couldn't find env FLEXRAN_VERSION!"
        exit 1
    fi
    envsubst < templates/pod_flexran_acc100.yaml.template > ${MANIFEST_DIR}/pod_flexran_du.yaml
    if [[ "${DU_FEC}" == "SW" ]]; then
        # remove intel.com/intel_fec_acc100: line
        sed -i '/intel.com\/intel_fec_acc100:/d' ${MANIFEST_DIR}/pod_flexran_du.yaml
    elif [[ "${DU_FEC}" == "N3000" ]]; then
        # replace with intel.com/intel_fec_5g
        sed -i 's/intel_fec_acc100:/intel_fec_5g:/g' ${MANIFEST_DIR}/pod_flexran_du.yaml
    elif [[ "${DU_FEC}" == "ACC100" ]]; then
        :
    else
        echo "invalid env DU_FEC: ${DU_FEC}"
        exit 1
    fi 
    echo "generating ${MANIFEST_DIR}/pod_flexran_du.yaml: done"
    
    #create flexran-test namespace
    if ! oc get namespace flexran-test 2>/dev/null; then
	echo "Create namespace flexran-test"
        oc create namespace flexran-test 
    fi
    


    if [[ "${timer_mode:-true}" == "true" ]]; then
        yq -i -y 'del(.metadata.annotations)' ${MANIFEST_DIR}/pod_flexran_du.yaml
    fi

    oc create -f ${MANIFEST_DIR}/pod_flexran_du.yaml
fi

wait_named_pod_in_namespace flexran-test flexran-du

