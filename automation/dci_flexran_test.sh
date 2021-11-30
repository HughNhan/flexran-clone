#!/bin/sh

set -euo pipefail

#dir=/root/flexran-repo/automation
dir=$1

cd $dir/

pwd=${PWD}

rm -rf "results/"
rm -rf "test_logs/"
mkdir -p "test_logs"
echo "##########  Enter automation direcoty: $pwd    #############" | tee -a "test_logs/automation.log"
echo "####  Run start.sh at "$(date +'%d/%m/%Y %H:%M:%S:%3N')"  ####" | tee -a "test_logs/automation.log"
echo | tee -a "test_logs/automation.log"
bash start.sh | tee -a "test_logs/automation.log"

echo "##########  start.sh finish at "$(date +'%d/%m/%Y %H:%M:%S:%3N')"   #############" | tee -a "test_logs/automation.log"



