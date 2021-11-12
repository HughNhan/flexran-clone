#!/bin/sh

#set -euo pipefail

#dir=/root/flexran-repo/automation
dir=$1

cd $dir/

pwd=${PWD}

echo | tee -a "test_logs/automation.log"
echo "##########  Enter automation direcoty: $pwd    #############" | tee -a "test_logs/automation.log"
echo "##########  Run cleanup.sh at "$(date +'%d/%m/%Y %H:%M:%S:%3N')"   #############" | tee -a "test_logs/automation.log"
echo  | tee -a "test_logs/automation.log"

bash cleanup.sh | tee -a "test_logs/automation.log"

echo "#######  cleanup.sh finish at "$(date +'%d/%m/%Y %H:%M:%S:%3N')"  ###########" | tee -a "test_logs/automation.log"

