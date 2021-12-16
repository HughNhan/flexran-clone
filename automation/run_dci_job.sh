#/bin/sh
set -ex

./ocp_cluster_install.sh

dci-openshift-app-agent-ctl -s -- -v -e kubeconfig_path=/root/.kube/config
