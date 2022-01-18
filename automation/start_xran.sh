#/bin/sh

source ./setting.env
source ./functions.sh

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
