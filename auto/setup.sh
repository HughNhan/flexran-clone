#!/bin/sh


if [[ -n "$1" && "$1" == "l2" ]]; then
    while ! pgrep l1app; do
        echo "waiting for l1"
	sleep 5
    done
    echo "starting l2"
    if [[ -e env.src ]]; then
        source /opt/auto/env.src
    else
        pushd /opt/flexran && source ./set_env_var.sh -d
    fi
    pushd /opt/flexran/bin/nr5g/gnb/testmac && ./l2.sh -e
    exit $?
fi

pip3 install pyyaml
# protecton starts here 
set -e

# if rcuc or ksoftirqd defined in env, set its priority
if [[ -n "${rcuc}" ]]; then
    for p in `pgrep rcuc`; do chrt -f --pid ${rcuc} $p; done
fi

if [[ -n "${ksoftirqd}" ]]; then
    for p in `pgrep ksoftirqd`; do chrt -f --pid ${ksoftirqd} $p; done    
fi

# write xml.out as tmp file for inspection
./cpu.py --l1xml phycfg_timer.xml --l2xml testmac_cfg.xml --cfg threads.yaml
# beautify the xml in 2nd stage tmp file
xmllint --format -o testmac_cfg.xml.generated testmac_cfg.xml.out
xmllint --format -o phycfg_timer.xml.generated phycfg_timer.xml.out
# overwrite
/bin/cp -f testmac_cfg.xml.generated /opt/flexran/bin/nr5g/gnb/testmac/testmac_cfg.xml
/bin/cp -f phycfg_timer.xml.generated /opt/flexran/bin/nr5g/gnb/l1/phycfg_timer.xml

# protection ends here
set +e

echo "starting l1"
if [[ -e env.src ]]; then
    source /opt/auto/env.src
else
    pushd /opt/flexran && source ./set_env_var.sh -d
fi
#tmux new-session -s l1 -d "pushd /opt/flexran/bin/nr5g/gnb/l1; ./l1.sh -e"
pushd /opt/flexran/bin/nr5g/gnb/l1 && ./l1.sh -e
exit $?
