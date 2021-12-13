#/bin/sh

set -evuo pipefail

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
#cp -R pod/cfg_examples/timer_mode_cfg_ns3000_debug.yaml pod/timer_mode_cfg.yaml
#### End of dci debug @80
sleep 5
./pod/pod_exec_updates.py -p flexran-du -d /opt/flexran/auto -c ./pod/timer_mode_cfg.yaml -f ./pod/autotest.py -f ./pod/cpu.py  -f ./pod/pod_exec_updates.py -f ./pod/process_testfile.py -f ./pod/read_yaml_write_xml.py -f ./pod/timer_mode_cfg.yaml -namespace ${FLAXRAN_DU_NS} -timeout 30

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
./pod/pod_exec_updates.py -p flexran-du -d /opt/flexran/auto -c ./pod/xran_mode_cfg.yaml -f ./pod/autotest.py -f ./pod/cpu.py  -f ./pod/pod_exec_updates.py -f ./pod/process_testfile.py -f ./pod/read_yaml_write_xml.py -f ./pod/xran_mode_cfg.yaml --xran --phystart -namespace ${FLAXRAN_DU_NS} -timeout 30

echo "Flexran tests finish at the end"
exit 0
