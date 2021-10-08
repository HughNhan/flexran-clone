#!/bin/sh

set -eu

print_usage() {
    declare -A arr
    arr+=( ["vfio"]="bind VFs to the vfio-pci driver"
           ["iavf"]="bind VFs to the iavf driver"
         )
    echo "Usage:"
    echo ""
    for key in ${!arr[@]}; do
        printf '%-15s: %s\n' "$key" "${arr[$key]}"
    done
    exit 1
}

get_pci_str() {
    pci_str=$(env | sed  -r -n 's/^PCIDEVICE_OPENSHIFT_IO.*=(.*)/\1/p' | sed 's/,/ /g')
    if [ -z "${pci_str}" ]; then
       echo "No VF is set via PCIDEVICE_OPENSHIFT_IO, is this a openshift pod?"
       exit 1
    fi
}

bind_driver () {
    driver=$1

    get_pci_str

    for vf_pci in ${pci_str}; do
        if [[ ! -e /sys/bus/pci/drivers/${driver}/${vf_pci} ]]; then
            if [[ -e /sys/bus/pci/devices/${vf_pci}/driver ]]; then
                echo ${vf_pci} > /sys/bus/pci/devices/${vf_pci}/driver/unbind
            fi
            device_id=$(lspci -s ${vf_pci} -n | awk '{print $3}' | sed 's/:/ /')
            if ! echo "${device_id}" > /sys/bus/pci/drivers/${driver}/new_id 2>&1 >/dev/null; then
                true
            fi
            sleep 1
            if [[ ! -e /sys/bus/pci/drivers/${driver}/${vf_pci} ]]; then
                echo ${vf_pci} > /sys/bus/pci/drivers/${driver}/bind
            fi
        fi
    done
}

bind_vfio () {
    bind_driver vfio-pci
}


bind_iavf () {
    bind_driver iavf
}

if (( $# != 1 )); then
    print_usage
else
    ACTION=$1
fi

case "${ACTION}" in
    vfio)
        bind_vfio 
    ;;
    iavf)
        bind_iavf
    ;;
    *)
        print_usage
esac

