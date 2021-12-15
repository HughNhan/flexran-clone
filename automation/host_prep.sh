#!/bin/sh
set -eu

source ./setting.env
source ./functions.sh

if [[ "${RUN_XRAN}" == "true" ]]; then
    echo "check kernel cmdline ..."
    for param in "iommu" "intel_iommu" "hugepagesz" "hugepages"; do
        if ! cat /proc/cmdline | egrep "${param}=" >/dev/null; then
            echo "please configure ${param} on kernel cmdline!"
            exit 1
        fi
    done
fi

for tool in python3 jq tmux; do
    if command -v ${tool} >/dev/null 2>&1; then
        echo "install ${tool} ..."
        dnf install -y ${tool} 
    fi
done

for pytool in yq; do
    pip3 install ${pytool} 
done

pip3 install kubernetes

if [[ "${UPI_INSTALL:-false}" == "true" ]]; then
    if [[ ! -e ~/flexran-site-manifests ]]; then
        echo "upi install is requested but ~/flexran-site-manifests does not exist!"
        exit 1
    fi
    if [[ -e ~/ocp-upi-install ]]; then
        /bin/rm -rf ~/ocp-upi-install
    fi
    git clone https://github.com/jianzzha/ocp-upi-install.git ~/ocp-upi-install
    /bin/cp -f ~/flexran-site-manifests/setup.conf.yaml ~/ocp-upi-install
    pushd ~/ocp-upi-install
    ./cleanup.sh
    ./setup.sh
    popd
fi

if ! oc get --request-timeout='10s' node; then
    echo "OCP cluster not ready !"
    exit 1
fi

