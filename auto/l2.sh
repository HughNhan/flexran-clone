#!/bin/sh
pushd /opt/flexran
source ./set_env_var.sh -d
pushd /opt/flexran/bin/nr5g/gnb/testmac 
./l2.sh -e
