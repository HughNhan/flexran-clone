#!/usr/bin/python3
# This is based on https://gist.github.com/amadorpahim/3062277

import os,re,copy,sys,getopt,yaml
import xml.etree.ElementTree as ET
from cpu import CpuResource

from read_yaml_write_xml import CfgData
from process_testfile import ProcessTestfile

procstatus = '/proc/self/status'

class Setting:
    @classmethod
    def update_cfg_files(cls, cfg: str, cpursc: CpuResource):
    # use self.cfg info to update the config files: phycfg_timer.xml, testmac_cfg.xml
    # assume these config files exist under the current directory
    # reference https://docs.google.com/document/d/1CLlfh2pt2eOxwus0gnOXuAnGT9yRYVu0Rrr8wTAP_0I/edit?usp=sharing
        CfgData.process_cfg_xml(cfg, cpursc)

    # Call the update_tesfile function of the ProcessTestfile class (in
    # process_testfile.py).
    @classmethod
    def update_testfile(cls, rsc, testfile, phystart_quick=False):
        ProcessTestfile.update_testfile(rsc, testfile, phystart_quick)

def main(name, argv):
    nosibling = False
    phystart = False
    cfg = "timer_mode_cfg.yaml"
    helpstr = name + " --testfile=<testfile path>"\
                     " --cfg=<yaml_cfg>"\
                     " --nosibling"\
                     " --phystart"\
                     "\n"
    try:
        opts, args = getopt.getopt(argv,"h",["testfile=", "cfg=", "nosibling", "phystart"])
    except getopt.GetoptError:
        print(helpstr)
        sys.exit(2)

    testfile_flag = False
    for opt, arg in opts:
        if opt == '-h':
            print(helpstr)
            sys.exit()
        elif opt in ("--testmac_dir"):
            testmac_dir = arg
        elif opt in ("--l1_dir"):
            l1_dir = arg
        elif opt in ("--testfile"):
            testfile = arg
        elif opt in ("--cfg"):
            cfg = arg
        elif opt in ("--nosibling"):
            nosibling = True
        elif opt in ("--phystart"):
            phystart = True

    status_content = open(procstatus).read().rstrip('\n')
    cpursc = CpuResource(status_content, nosibling)

    Setting.update_cfg_files(cfg, cpursc)
    # NOTE: QUICK PHYSTART NOTED BY TRUE, CHANGE FOR REAL TESTS.
    Setting.update_testfile(cpursc, testfile, phystart)

    print('Files updated.')

if __name__ == "__main__":
     main(sys.argv[0], sys.argv[1:])
