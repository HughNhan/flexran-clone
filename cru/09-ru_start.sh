#!/bin/sh
set -eu

source ./setting.env
source ./functions.sh

if [[ ! -f ${ORU_DIR}/usecase_ru.cfg.orig ]]; then
    #HN Crucible saves orig file
    cp ${ORU_DIR}/usecase_ru.cfg  ${ORU_DIR}/usecase_ru.cfg.orig
fi

echo "updating cpu setting in ${ORU_DIR}/usecase_ru.cfg"

cpu_cache_dir=$(mktemp -d)

isolated_cpus=$(cat /proc/cmdline | sed -n -r 's/.* isolcpus=([0-9,\,\-]+) .*/\1/p')
if [[ -z "${isolated_cpus}" ]]; then
    echo "no isolated_cpus on kernel cmdline, use default Cpus_allowed_list"
    egrep 'Cpus_allowed_list:' /proc/self/status > ${cpu_cache_dir}/procstatus
else
    echo "found isolated_cpus on kernel cmdline"
    echo "Cpus_allowed_list: ${isolated_cpus}" > ${cpu_cache_dir}/procstatus 
fi

PYTHON=$(get_python_exec)
core=$(${PYTHON} cpu_cmd.py --proc=${cpu_cache_dir}/procstatus --dir ${cpu_cache_dir} allocate-core)
sed -i -r "s/^(ioCore)=.*/\1=${core}/" ${ORU_DIR}/usecase_ru.cfg

cpumask=$(${PYTHON} cpu_cmd.py --proc=${cpu_cache_dir}/procstatus --dir ${cpu_cache_dir} allocate-cpu-mask 2)

sed -i -r "s/^(ioWorker)=.*/\1=${cpumask}/" ${ORU_DIR}/usecase_ru.cfg

echo "cpu setting updated"

/bin/rm -rf ${cpu_cache_dir}

echo "starting ru"

echo "cd ${FLEXRAN_DIR}; source ./set_env_var.sh -d; cd ${ORU_DIR}; ./run_o_ru.sh"
#echo "HN dry run"; exit
ru_cmd="cd ${FLEXRAN_DIR}; source ./set_env_var.sh -d; cd ${ORU_DIR}; ./run_o_ru.sh"

tmux kill-session -t ru 2>/dev/null || true
sleep 1
tmux new-session -s ru -d "${ru_cmd}" 
sleep 1
if ! tmux ls | grep ru; then
    echo "failed to start ru"
    exit 1
else
    echo "ru started"
fi

