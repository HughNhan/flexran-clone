get_python_exec () {
    local py_exec
    if command -v python3 >/dev/null 2>&1; then
        py_exec=python3
    else
        for x in $(ls /usr/bin/python3); do
	    if command -v $x >/dev/null 2>&1; then
                py_exec=$x
                break
            else
               py_exec=""
            fi
        done
    fi
    if [[ -z "${py_exec}" ]]; then
        echo "command python and python3 not available!"
        exit 1
    fi
    echo ${py_exec}
}

bind_driver () {
    local driver=$1
    local pci=$2
    local original_path=$(realpath /sys/bus/pci/devices/${pci}/driver)
    local new_path=/sys/bus/pci/drivers/${driver}
    if [[ ! -e ${new_path}/${pci} ]]; then
        echo ${pci} > ${original_path}/unbind  || true
        echo ${driver} > /sys/bus/pci/devices/${pci}/driver_override  || true
        echo ${pci} > ${new_path}/bind  || true
        if [[ ! -e ${new_path}/${pci} ]]; then
            echo "failed to bind ${pci} to ${new_path}"
            exit 1 
        fi
    fi
}

get_ocp_channel () {
    local channel=$(oc get clusterversion -o json | jq -r '.items[0].spec.channel' | sed -r -n 's/.*-(.*)/\1/p')
    echo ${channel}
}

get_mcp_progress_status () {
    local status=$(oc get mcp worker-cnf -o json | jq -r '.status.conditions[] | select(.type == "Updating") | .status')
    echo ${status}
}

wait_mcp () {
    sleep 60
    local status=$(get_mcp_progress_status)
    local count=200
    while [[ $status != "False" ]]; do
        if ((count == 0)); then
            echo "timeout waiting for mcp complete on the baremetal host!"
            exit 1
        fi
        count=$((count-1))
        echo "waiting for mcp complete on the baremetal host ..."
        sleep 5
        status=$(get_mcp_progress_status)
    done
}

wait_pod_in_namespace () {
    local namespace=$1
    local count=100
    while ! oc get pods -n ${namespace} 2>/dev/null | grep Running; do
        if ((count == 0)); then
            echo "timeout waiting for pod in ${namespace}!"
            exit 1
        fi
        count=$((count-1))
        echo "waiting for pod in ${namespace} ..."
        sleep 5
    done
    echo "pod in ${namespace}: up"
}

wait_named_pod_in_namespace () {
    local namespace=$1
    local podpattern=$2
    local count=100
    while ! oc get pods -n ${namespace} 2>/dev/null | grep ${podpattern} | grep Running; do
        if ((count == 0)); then
            echo "timeout waiting for pod in ${namespace}!"
            exit 1
        fi
        count=$((count-1))
        echo "waiting for pod pattern ${podpattern} in ${namespace} ..."
        sleep 5
    done
    echo "pod ${podpattern} in ${namespace}: up"
}

exec_over_ssh () {
    local nodename=$1
    local cmd=$2
    local ssh_options="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    local ip_addr=$(oc get node ${nodename} -o json | jq -r '.status.addresses[] | select(.type=="InternalIP") | .address')
    local ssh_output=$(ssh ${ssh_options} core@${ip_addr} "$cmd")
    echo "${ssh_output}"
}

set_registry () {
    OPENSHIFT_SECRET_FILE=pull_secret.json
    oc get secret/pull-secret -n openshift-config --template='{{index .data ".dockerconfigjson" | base64decode}}' > ${OPENSHIFT_SECRET_FILE}
    oc registry login --skip-check --registry="${IMAGE_REPO}" --auth-basic="${REGISTRY_USER}:${REGISTRY_PASSWORD}" --to=${OPENSHIFT_SECRET_FILE}
    oc set data secret/pull-secret -n openshift-config --from-file=.dockerconfigjson=${OPENSHIFT_SECRET_FILE}
    REGISTRY_CERT="domain.crt"
    if [[ ! -e ${REGISTRY_CERT} ]]; then
        echo "${REGISTRY_CERT} not present in current folder, downloading from REGISTRY_SSL_CERT_URL ..."
        curl -L -o ${REGISTRY_CERT} ${REGISTRY_SSL_CERT_URL}
    fi
    oc delete configmap registry-cas -n openshift-config 2>/dev/null || true
    oc create configmap registry-cas -n openshift-config --from-file=$(echo ${IMAGE_REPO} | sed s/:/../)=${REGISTRY_CERT}
    oc patch image.config.openshift.io/cluster --patch '{"spec":{"additionalTrustedCA":{"name":"registry-cas"}}}' --type=merge
}

parse_args() {
    USAGE="Usage: $0 [options]
Options:
    -n             Do not wait
    -h             This
"
    while getopts "hn" OPTION
    do
        case $OPTION in
            n) WAIT_MCP="false" ;;
            h) echo "$USAGE"; exit ;;
            *) echo "$USAGE"; exit 1;;
        esac
    done

    WAIT_MCP=${WAIT_MCP:-"true"}
}

