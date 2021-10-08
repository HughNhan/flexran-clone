#!/bin/sh

set -eu

source ./setting.env
source ./functions.sh

echo "updating cpu setting in ${ORU_DIR}/usecase_ru.cfg"

cpu_cache_dir=$(mktemp -d)

isolated_cpus=$(cat /sys/devices/system/cpu/nohz_full)
if [[ -z "${isolated_cpus}" ]]; then
    isolated_cpus=$(cat /proc/cmdline | sed -n -r 's/.* isolcpus=([0-9,\,\-]+) .*/\1/p')
fi
if [[ -z "${isolated_cpus}" ]]; then
    echo "please configure isolcpus with RT kernel!"
    exit 1
fi

# build a fake procstatus file using above cpuset
echo "Cpus_allowed_list: ${isolated_cpus}" > ${cpu_cache_dir}/procstatus

PYTHON=$(get_python_exec)
core=$(${PYTHON} cpu_cmd.py --proc=${cpu_cache_dir}/procstatus --dir ${cpu_cache_dir} allocate-core)
sed -i -r "s/^(ioCore)=.*/\1=${core}/" ${ORU_DIR}/usecase_ru.cfg

cpumask=$(${PYTHON} cpu_cmd.py --proc=${cpu_cache_dir}/procstatus --dir ${cpu_cache_dir} allocate-cpu-mask 2)
sed -i -r "s/^(ioWorker)=.*/\1=${cpumask}/" ${ORU_DIR}/usecase_ru.cfg

echo "cpu setting updated"

/bin/rm -rf ${cpu_cache_dir}

echo "starting ru"

cd ${ORU_DIR}

ru_cmd="./run_o_ru.sh"

tmux kill-session -t ru 2>/dev/null || true
tmux new-session -s ru -d "${ru_cmd}" 

if ! tmux ls | grep ru; then
    echo "failed to start ru"
    exit 1
else
    echo "ru started"
fi

