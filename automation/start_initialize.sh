#/bin/sh

set -euo pipefail

parse_args() {
   USAGE="Usage: $0 [options]
Options:
   [-s <Site specific manifest repo url>]  Download manifests from this repo

This script starts a end to end flexran setup and test.
"
    while getopts "s:h" opt
    do
        case ${opt} in
            s) manifest_url=$OPTARG ;;
            h) echo "$USAGE"; exit 0 ;;
            :) echo $USAGE; exit 1 ;;
            *) echo $USAGE; exit 1 ;;
        esac
    done
}

parse_args $@

if [[ -n ${manifest_url:-''} ]]; then
    if [[ -e ~/flexran-site-manifests ]]; then
        /bin/rm -rf ~/flexran-site-manifests
    fi
    git clone ${manifest_url} ~/flexran-site-manifests
    if [[ -e ~/flexran-site-manifests/setting.env ]]; then
        /bin/cp -f ~/flexran-site-manifests/setting.env ./setting.env
    fi
fi

####Following line is for dci debug @80
#cp -R pod/cfg_examples/setting_timermode_only.env setting.env
#### End of dci debug @80

source ./setting.env
source ./functions.sh

echo "prepare host ..."
./host_prep.sh

./create_mcp.sh

pause_mcp
echo "setup du for timer mode test ..."
./performance_operator_install.sh -n
./fec_operator_install.sh -n

echo "wait mcp to complete ..."
wait_mcp

#create flexran test namespace
if ! oc get namespace ${FLEXRAN_DU_NS} 2>/dev/null; then
    echo "Create namespace ${FLEXRAN_DU_NS}"
    oc create namespace ${FLEXRAN_DU_NS}
fi

##### now run the timer mode test suites ####
./du_pod_install.sh

####Following line is for dci debug @80
#oc cp ./pod/cfg_examples/clxsp_mu0_20mhz_4x4_hton.cfg_debug flexran-du:/opt/flexran/bin/nr5g/gnb/testmac/cascade_lake-sp/clxsp_mu0_20mhz_4x4_hton.cfg
#cp -R pod/cfg_examples/timer_mode_cfg_ns3000_debug.yaml pod/timer_mode_acc100_cfg.yaml
#### End of dci debug @80
sleep 5
./pod/pod_exec_updates.py -p flexran-du -d /opt/flexran/auto -c ./pod/timer_mode_acc100_cfg.yaml -f ./pod/autotest.py -f ./pod/cpu.py  -f ./pod/pod_exec_updates.py -f ./pod/process_testfile.py -f ./pod/read_yaml_write_xml.py -f ./pod/timer_mode_acc100_cfg.yaml -namespace ${FLEXRAN_DU_NS} -timeout 60

if [[ "${RUN_XRAN:-false}" == "false" ]]; then
    echo "test complete"
    exit 0
fi

#### the following is prepare for front haul test ####
./du_pod_cleanup.sh


pause_mcp
./ptp_operator_install.sh -n
./sriov_operator_install.sh -n

echo "wait mcp to complete ..."
wait_mcp

# remove below line after fec operator bug fixed
# ./fec_operator_install.sh

echo "setup ru ..."


./ru_sriov.sh setup
./ru_ptp.sh setup
./ru_start.sh

##### now run the front haul test ####
./du_pod_install.sh -x

sleep 5
./pod/pod_exec_updates.py -p flexran-du -d /opt/flexran/auto -c ./pod/xran_mode_cfg.yaml -f ./pod/autotest.py -f ./pod/cpu.py  -f ./pod/pod_exec_updates.py -f ./pod/process_testfile.py -f ./pod/read_yaml_write_xml.py -f ./pod/xran_mode_cfg.yaml --xran --phystart -namespace ${FLEXRAN_DU_NS} -timeout 60

echo "Flexran tests finish at the end"
exit 0
