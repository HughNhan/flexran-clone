#/bin/sh

set -euo pipefail

source ./setting.env
source ./functions.sh

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

exit 0
