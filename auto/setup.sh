#!/bin/sh
#./cpuinfo -l1cfg phycfg_timer.xml -l2cfg testmac_cfg.xml
#xmllint --format -o phycfg_timer.xml.generated phycfg_timer.xml.out
#xmllint --format -o testmac_cfg.xml.generated testmac_cfg.xml.out
./cpu.py --l1xml phycfg_timer.xml --l2xml testmac_cfg.xml --cfg threads.yaml
xmllint --format -o testmac_cfg.xml.generated testmac_cfg.xml.out
xmllint --format -o phycfg_timer.xml.generated phycfg_timer.xml.out
/bin/cp -f testmac_cfg.xml.generated /opt/flexran/bin/nr5g/gnb/testmac/testmac_cfg.xml
/bin/cp -f phycfg_timer.xml.generated /opt/flexran/bin/nr5g/gnb/l1/phycfg_timer.xml
pushd /opt/flexran && source ./set_env_var.sh -d
#tmux new-session -s l1 -d "pushd /opt/flexran/bin/nr5g/gnb/l1; ./l1.sh -e"
pushd /opt/flexran/bin/nr5g/gnb/l1 && ./l1.sh -e

