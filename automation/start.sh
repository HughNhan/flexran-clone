#/bin/sh

set -euo pipefail

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

##### now run the timer mode test suites ####
./du_pod_install.sh

./pod/pod_exec_updates.py -p flexran-du -d /opt/flexran/auto -testmac /opt/flexran/bin/nr5g/gnb/testmac -l1 /opt/flexran/bin/nr5g/gnb/l1 -c ./pod/timer_mode_cfg.yaml -f ./pod/autotest.py -f ./pod/cpu.py -f ./pod/pod_exec.py -f ./pod/pod_exec_updates.py -f ./pod/pod_flexran_sw.yaml -f ./pod/process_testfile.py -f ./pod/read_yaml_write_xml.py -f ./pod/timer_mode_cfg.yaml

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

./pod/pod_exec_updates.py -p flexran-du -d /opt/flexran/auto -testmac /opt/flexran/bin/nr5g/gnb/testmac -l1 /opt/flexran/bin/nr5g/gnb/l1/orancfg/sub3_mu0_10mhz_4x4/gnb/ -c ./pod/xran_mode_cfg.yaml -f ./pod/autotest.py -f ./pod/cpu.py -f ./pod/pod_exec.py -f ./pod/pod_exec_updates.py -f ./pod/pod_flexran_sw.yaml -f ./pod/process_testfile.py -f ./pod/read_yaml_write_xml.py -f ./pod/xran_mode_cfg.yaml --xran --phystart

echo "test complete"
exit 0
