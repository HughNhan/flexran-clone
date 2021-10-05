bind_driver () {
    driver=$1
    pci=$2

    if [[ ! -e /sys/bus/pci/drivers/${driver}/${pci} ]]; then
        if [[ -e /sys/bus/pci/devices/${pci}/driver ]]; then
            echo ${pci} > /sys/bus/pci/devices/${pci}/driver/unbind
        fi
        device_id=$(lspci -s ${pci} -n | awk '{print $3}' | sed 's/:/ /')
        if ! echo "${device_id}" > /sys/bus/pci/drivers/${driver}/new_id 2>&1 >/dev/null; then
            true
        fi
        if [[ ! -e /sys/bus/pci/drivers/${driver}/${pci} ]]; then
            echo ${pci} > /sys/bus/pci/drivers/${driver}/bind
        fi
    fi
}

get_mcp_progress_status () {
    status=$(oc get mcp | awk '/worker-cnf/{if(match($2, /rendered-/)){print $3} else{print $4}}')
    echo ${status}
}
