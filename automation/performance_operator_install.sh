#!/bin/sh

set -euo pipefail

source ./setting.env
source ./functions.sh

oc label --overwrite node ${BAREMETAL_WORKER} node-role.kubernetes.io/worker-cnf=""

###### install performnance operator #####
# skip if performance operator subscription already exists 
if ! oc get Subscription performance-addon-operator -n openshift-performance-addon; then 
    echo "generating ${MANIFEST_DIR}/sub-perf.yaml ..."
    export OCP_CHANNEL=$(oc get clusterversion -o yaml | yq -r '.items[0].spec.channel' | sed -r -n 's/.*-(.*)/\1/p')
    envsubst < templates/sub-perf.yaml.template > ${MANIFEST_DIR}/sub-perf.yaml
    oc create -f ${MANIFEST_DIR}/sub-perf.yaml
    echo "generating ${MANIFEST_DIR}/sub-perf.yaml: done"
fi

count=100
while ! oc get pods -n openshift-performance-addon | grep Running; do
    if ((count == 0)); then
        echo "timeout waiting for openshift-performance-addon operator!"
        exit 1
    fi 
    count=$((count-1))
    echo "waiting for openshift-performance-addon operator ..."
    sleep 3
done
echo "openshift-performance-addon operator: up"

###### generate performance profile ######
echo "Acquiring cpu info from worker node ${BAREMETAL_WORKER} ..."
ssh_options="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
all_cpus=$(ssh ${ssh_options} core@${BAREMETAL_WORKER} lscpu | awk '/On-line CPU/{print $NF;}')
export DU_RESERVED_CPUS=$(ssh ${ssh_options} core@${BAREMETAL_WORKER} cat /sys/bus/cpu/devices/cpu0/topology/thread_siblings_list)
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

echo "apply ${MANIFEST_DIR}/performance_profile.yaml: done"
