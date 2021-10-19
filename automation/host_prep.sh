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
