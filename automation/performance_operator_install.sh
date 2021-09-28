#!/bin/sh

set -euo pipefail

source ./setting.env

###### install performnance operator #####






###### generate performance profile ######
echo "Acquiring cpu info from worker node ${BAREMETAL_WORKER}"
ssh_options="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
all_cpus=$(ssh ${ssh_options} core@${BAREMETAL_WORKER} lscpu | awk '/On-line CPU/{print $NF;}')
export DU_RESERVED_CPUS=$(ssh ${ssh_options} core@${BAREMETAL_WORKER} cat /sys/bus/cpu/devices/cpu0/topology/thread_siblings_list)
export DU_ISOLATED_CPUS=$(python cpu_cmd.py cpuset-substract ${all_cpus} ${DU_RESERVED_CPUS})
echo "Done"

echo "generating manifests"
mkdir -p ${MANIFEST_DIR}/
envsubst < templates/performance_profile.yaml.template > ${MANIFEST_DIR}/performance_profile.yaml
echo "Done"i


##### apply performance profile ######
