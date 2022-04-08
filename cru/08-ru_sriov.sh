#!/bin/sh
set -euo pipefail

source ./functions.sh

source ./setting.env

if [[ ! -f ${ORU_DIR}/run_o_ru.sh.orig ]]; then
   # CRU/Cru HN save orig file
   cp ${ORU_DIR}/run_o_ru.sh ${ORU_DIR}/run_o_ru.sh.orig
fi


if [[ ! -e /sys/class/net/${RU_SRIOV_INTERFACE} ]]; then
    echo "RU_SRIOV_INTERFACE ${RU_SRIOV_INTERFACE} not exists"
    exit 1
fi


print_usage() {
    declare -A arr
    arr+=( ["setup"]="setup SRIOV on RU"
           ["clean"]="cleanup SRIOV on RU"
         )
    echo "Usage:"
    echo ""
    for key in ${!arr[@]}; do
        printf '%-15s: %s\n' "$key" "${arr[$key]}"
    done
    exit 1
}

setup() {
    echo "Setting up SRIOV on RU ..."


    echo "creating VFs on ${RU_SRIOV_INTERFACE}"
    echo 2 > /sys/class/net/${RU_SRIOV_INTERFACE}/device/sriov_numvfs    
    ip link set dev ${RU_SRIOV_INTERFACE} vf 0 vlan 10 mac 00:11:22:33:00:01 spoofchk off
    ip link set dev ${RU_SRIOV_INTERFACE} vf 1 vlan 20 mac 00:11:22:33:00:11 spoofchk off
    # sleep a little so dmesg of VFs and binds kept in sequences. Better debug
    sleep 10
    echo "bind VF to vfio-pci"
    modprobe vfio-pci
    vfs_str=""
    for v in 0 1; do
        vf_pci=$(realpath /sys/class/net/${RU_SRIOV_INTERFACE}/device/virtfn${v} | awk -F '/' '{print $NF}')
        bind_driver vfio-pci ${vf_pci}
        if [[ -z "${vfs_str}" ]]; then
            vfs_str=${vf_pci}
        else
            vfs_str="${vfs_str},${vf_pci}"
        fi
    done

    echo "SRIOV setup on RU: done"
}     

clean() {
    echo "Cleaning up SRIOV on RU"
    echo 0 > /sys/class/net/${RU_SRIOV_INTERFACE}/device/sriov_numvfs
    echo "SRIOV cleanup on RU: done"
}

update_run_o_ru_file() {
    if [[ -n "${vfs_str}" ]]; then
        sed -i -r "s/(.*vf_addr_o_xu_a).*/\1 \"${vfs_str}\"/" ${ORU_DIR}/run_o_ru.sh
    fi
}

if (( $# != 1 )); then
    print_usage
else
    ACTION=$1
fi

case "${ACTION}" in
    setup)
        setup 
        update_run_o_ru_file
    ;;
    clean)
        clean 
    ;;
    *)
        print_usage
esac


