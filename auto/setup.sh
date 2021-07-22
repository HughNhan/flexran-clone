#!/bin/sh

wait_l1 () {
    while ! pgrep l1app; do
        echo "waiting for l1"
        sleep 5
    done
}

adjust_kthreads () {
    # if rcuc or ksoftirqd defined in env, set its priority
    if [[ -n "${rcuc}" ]]; then
        for p in `pgrep rcuc`; do chrt -f --pid ${rcuc} $p; done
    fi
    
    if [[ -n "${ksoftirqd}" ]]; then
        for p in `pgrep ksoftirqd`; do chrt -f --pid ${ksoftirqd} $p; done    
    fi
} 

bind_vfio () {
    pci_str=$(env | sed  -r -n 's/^PCIDEVICE_OPENSHIFT_IO.*=(.*)/\1/p' | sed 's/,/ /g')
    if [ -z "${pci_str}" ]; then
       echo "No VF is set via PCIDEVICE_OPENSHIFT_IO, is this a openshift pod?"
       exit 1
    fi

    for vf_pci in ${pci_str}; do
        if [[ ! -e /sys/bus/pci/drivers/vfio-pci/${vf_pci} ]]; then
            if [[ -e /sys/bus/pci/devices/${vf_pci}/driver ]]; then
                echo ${vf_pci} > /sys/bus/pci/devices/${vf_pci}/driver/unbind
                kernel_driver_path=$(realpath /sys/bus/pci/devices/${vf_pci}/driver)
            fi
            device_id=$(lspci -s ${vf_pci} -n | awk '{print $3}' | sed 's/:/ /')
            echo "${device_id}" > /sys/bus/pci/drivers/vfio-pci/new_id
            if [[ ! -e /sys/bus/pci/drivers/vfio-pci/${vf_pci} ]]; then
                echo ${vf_pci} > /sys/bus/pci/drivers/vfio-pci/bind
            fi
        fi
    done
}

bind_kernel_driver () {
    for vf_pci in ${pci_str}; do
        if [[ -e /sys/bus/pci/devices/${vf_pci}/driver ]]; then
            echo ${vf_pci} > /sys/bus/pci/devices/${vf_pci}/driver/unbind
        fi
        echo ${vf_pci} > ${kernel_driver_path}/bind
    done
}

if [[ -e env.src ]]; then
    source ./env.src
else
    pushd /opt/flexran && source ./set_env_var.sh -d
    popd
fi

set -e

if [[ -z "$1" ]]; then
    echo "$0 <l1-timer|l2-timer|l1-xran|l2-xran>"
    exit 1
fi

testfile=`pwd`/${testfile:-cascade_lake_mu0_20mhz_6cell.cfg}
if [[ ! -e "${testfile}" ]]; then
    if [[ "$1" == "l2-xran" || "$1" == "l1-xran" ]]; then
        echo "testfile ${testfile} not exists!"
        exit 1
    fi
fi

if [[ "$1" == "l2-xran" ]]; then
    wait_l1    
    pushd /opt/flexran/bin/nr5g/gnb/testmac && ./l2.sh --testfile=${testfile} 
elif [[ "$1" == "l2-timer" ]]; then
    wait_l1
    echo "starting l2"
    pushd /opt/flexran/bin/nr5g/gnb/testmac && ./l2.sh -e
elif [[ "$1" == "l1-xran" ]]; then
    adjust_kthreads
    vf_pci=$(env | sed  -r -n 's/^PCIDEVICE_OPENSHIFT_IO.*=([0-9a-fA-F\:\.]+).*/\1/p')
    if [ -z "${vf_pci}" ]; then
       echo "No VF is set via PCIDEVICE_OPENSHIFT_IO, is this a openshift pod?"
       exit 1
    fi
    
    # unbound VF from kernel and rebind to dpdk driver 
    bind_vfio

    echo "fixing xml files"
    sed  -i -r 's/^(\s+)<(\w+)>(.+)<.+/\1<\2>\3<\/\2>/' /opt/flexran/bin/nr5g/gnb/l1/phycfg_xran.xml
    sed  -i -r 's/^(\s+)<(\w+)>(.+)<.+/\1<\2>\3<\/\2>/' /opt/flexran/bin/nr5g/gnb/testmac/testmac_cfg.xml
    sed -i -r 's/^(\s+)<(\w+)>(.+)<.+/\1<\2>\3<\/\2>/' /opt/flexran/bin/nr5g/gnb/l1/xrancfg_sub6.xml
    echo "starting l1"
    ./cpu.py --l1xml /opt/flexran/bin/nr5g/gnb/l1/phycfg_xran.xml --l2xml /opt/flexran/bin/nr5g/gnb/testmac/testmac_cfg.xml --xrancfg /opt/flexran/bin/nr5g/gnb/l1/xrancfg_sub6.xml --testfile=${testfile} --cfg threads.yaml
    xmllint --format -o phycfg_xran.xml.generated phycfg_xran.xml.out
    sed -i -r 's/^(\s+)<dpdkMemorySize>.+/\1<dpdkMemorySize>6144<\/dpdkMemorySize>/' phycfg_xran.xml.generated
    /bin/cp -f phycfg_xran.xml.generated /opt/flexran/bin/nr5g/gnb/l1/phycfg_xran.xml
    xmllint --format -o testmac_cfg.xml.generated testmac_cfg.xml.out
    /bin/cp -f testmac_cfg.xml.generated /opt/flexran/bin/nr5g/gnb/testmac/testmac_cfg.xml
    xmllint --format -o xrancfg_sub6.xml.generated xrancfg_sub6.xml.out
    /bin/cp -f xrancfg_sub6.xml.generated /opt/flexran/bin/nr5g/gnb/l1/xrancfg_sub6.xml
    pushd /opt/flexran/bin/nr5g/gnb/l1 && ./l1.sh -xran
    # rebind ${vf_pci} to kernel driver
    if [[ -n "${kernel_driver_path}" ]]; then
        bind_kernel_driver
    fi
 
elif [[ "$1" == "l1-timer" ]]; then
    adjust_kthreads
    echo "fixing xml files"
    sed  -i -r 's/^(\s+)<(\w+)>(.+)<.+/\1<\2>\3<\/\2>/' /opt/flexran/bin/nr5g/gnb/testmac/testmac_cfg.xml
    sed  -i -r 's/^(\s+)<(\w+)>(.+)<.+/\1<\2>\3<\/\2>/' /opt/flexran/bin/nr5g/gnb/l1/phycfg_timer.xml    
    # write xml.out as tmp file for inspection
    ./cpu.py --l1xml /opt/flexran/bin/nr5g/gnb/l1/phycfg_timer.xml --l2xml /opt/flexran/bin/nr5g/gnb/testmac/testmac_cfg.xml --cfg threads.yaml
    # beautify the xml in 2nd stage tmp file
    xmllint --format -o testmac_cfg.xml.generated testmac_cfg.xml.out 
    xmllint --format -o phycfg_timer.xml.generated phycfg_timer.xml.out
    sed -i -r 's/^(\s+)<dpdkMemorySize>.+/\1<dpdkMemorySize>6144<\/dpdkMemorySize>/' phycfg_timer.xml.generated 
    # overwrite
    /bin/cp -f testmac_cfg.xml.generated /opt/flexran/bin/nr5g/gnb/testmac/testmac_cfg.xml
    /bin/cp -f phycfg_timer.xml.generated /opt/flexran/bin/nr5g/gnb/l1/phycfg_timer.xml
    
    # protection ends here
    set +e
    
    echo "starting l1"
    #tmux new-session -s l1 -d "pushd /opt/flexran/bin/nr5g/gnb/l1; ./l1.sh -e"
    pushd /opt/flexran/bin/nr5g/gnb/l1 && ./l1.sh -e
fi

exit $?
