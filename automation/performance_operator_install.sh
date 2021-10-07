#!/bin/sh

set -euo pipefail

source ./setting.env
source ./functions.sh

parse_args $@

oc label --overwrite node ${BAREMETAL_WORKER} node-role.kubernetes.io/worker-cnf=""

###### install performnance operator #####
# skip if performance operator subscription already exists 
if ! oc get Subscription performance-addon-operator -n openshift-performance-addon 2>/dev/null; then 
    echo "generating ${MANIFEST_DIR}/sub-perf.yaml ..."
    export OCP_CHANNEL=$(get_ocp_channel)
    envsubst < templates/sub-perf.yaml.template > ${MANIFEST_DIR}/sub-perf.yaml
    oc create -f ${MANIFEST_DIR}/sub-perf.yaml
    echo "generating ${MANIFEST_DIR}/sub-perf.yaml: done"
fi

wait_pod_in_namespace openshift-performance-addon

###### generate performance profile ######
echo "Acquiring cpu info from worker node ${BAREMETAL_WORKER} ..."
all_cpus=$(exec_over_ssh ${BAREMETAL_WORKER} lscpu | awk '/On-line CPU/{print $NF;}')
export DU_RESERVED_CPUS=$(exec_over_ssh ${BAREMETAL_WORKER} "cat /sys/bus/cpu/devices/cpu0/topology/thread_siblings_list")
export DU_ISOLATED_CPUS=$(python cpu_cmd.py cpuset-substract ${all_cpus} ${DU_RESERVED_CPUS})
echo "Acquiring cpu info from worker node ${BAREMETAL_WORKER}: done"

echo "generating ${MANIFEST_DIR}/performance_profile.yaml ..."
mkdir -p ${MANIFEST_DIR}/
envsubst < templates/performance_profile.yaml.template > ${MANIFEST_DIR}/performance_profile.yaml
echo "generating ${MANIFEST_DIR}/performance_profile.yaml: done"

##### apply performance profile ######
if ! oc get mcp worker-cnf 2>/dev/null; then
    echo "create mcp for worker-cnf ..."
    envsubst < templates/mcp-worker-cnf.yaml.template > ${MANIFEST_DIR}/mcp-worker-cnf.yaml
    oc create -f ${MANIFEST_DIR}/mcp-worker-cnf.yaml
    echo "create mcp for worker-cnf: done"
fi

echo "apply ${MANIFEST_DIR}/performance_profile.yaml ..."
oc apply -f ${MANIFEST_DIR}/performance_profile.yaml 

if [[ "${WAIT_MCP}" == "true" ]]; then
    wait_mcp
fi

echo "apply ${MANIFEST_DIR}/performance_profile.yaml: done"
