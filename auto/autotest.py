#!/usr/bin/python3
# This is based on https://gist.github.com/amadorpahim/3062277

import os,re,copy,sys,getopt,yaml
import xml.etree.ElementTree as ET
from cpu import CpuResource

from read_yaml_write_xml import CfgThreadData

procstatus = '/proc/self/status'

class Setting:
    def __init__(self, cfg=False):
        if cfg:
            try:
                f = open(cfg, 'r')
                self.cfg = yaml.load(f)
                f.close()
            except:
                sys.exit("can't process %s" %(cfg))

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            print('exit')
            self.f.close()
        except:
            sys.exit("can't close %s" %(f))

    @classmethod
    def update_cfg_files(cls, cfg: str, cpursc: CpuResource):
    # use self.cfg info to update the config files: phycfg_timer.xml, testmac_cfg.xml
    # assume these config files exist under the current directory
    # reference https://docs.google.com/document/d/1CLlfh2pt2eOxwus0gnOXuAnGT9yRYVu0Rrr8wTAP_0I/edit?usp=sharing
        CfgThreadData.update_threads_cfg_xml(cfg, cpursc)

    # A function to take the setcore maps in the config file and allocate
    # relevant cpus on the current machine, creating a new map and writing it
    # in place, always allocating siblings.
    #
    # References:
    #   https://stackoverflow.com/questions/38935169/convert-elements-of-a-list-into-binary
    #   https://stackoverflow.com/questions/21409461/binary-list-from-indices-of-ascending-integer-list
    def update_testfile(self, rsc, testfile):
        print('Updating testfile...')
        try:
            f = open(testfile, 'r')
            cfg = list(f)
            f.close()
        except:
            sys.exit("can't open %s" %(cfg))
        line_index = 0
        for line in cfg:
            if 'setcore' in line:
                setcore_index = line.index('setcore')
                # The number of cpus (cores or threads, depening on hyperthreading, needed.)
                # Take the string, convert to hex, convert to binary, count the 1s.
                num_cpus = (bin(int(line[setcore_index + len('setcore'):].strip(), 16))[2:]).count('1')
                # Allocate siblings based on the current setcore.
                cpus = rsc.allocate_siblings(num_cpus)
                # Create a list of binary digits based off CPU indices.
                new_setcore_list = [int(i in cpus) for i in range(max(cpus)+1)]
                # Revere the list, then create the binary number.
                new_setcore_list.reverse()
                new_setcore_binary = 0
                for digit in new_setcore_list:
                    new_setcore_binary = 2 * new_setcore_binary + digit
                # Create the hex representation and replace the old setcore
                new_setcore_hex = ' ' + hex(new_setcore_binary) + '\n'
                cfg[line_index] = line.replace(line[setcore_index + len('setcore'):], new_setcore_hex)

            line_index += 1

        # Write the new configuration to the same file.
        try:
            f = open(testfile, 'w')
            f.writelines(cfg)
        except:
            sys.exit("can't write %s" %(cfg))
        print('New testfile written.')
        f.close()

def main(name, argv):
    nosibling = False
    cfg = "threads.yaml"
    helpstr = name + " --testfile=<testfile path>"\
                     " --cfg=<yaml_cfg>"\
                     " --nosibling"\
                     "\n"
    try:
        opts, args = getopt.getopt(argv,"h",["testfile=", "cfg=", "nosibling"])
    except getopt.GetoptError:
        print(helpstr)
        sys.exit(2)

    testfile_flag = False
    for opt, arg in opts:
        if opt == '-h':
            print(helpstr)
            sys.exit()
        elif opt in ("--testfile"):
            testfile = arg
            testfile_flag = True
        elif opt in ("--cfg"):
            cfg = arg
        elif opt in ("--nosibling"):
            nosibling = True

    status_content = open(procstatus).read().rstrip('\n')
    cpursc = CpuResource(status_content, nosibling)

    if testfile_flag == True:
        setting = Setting()
        setting.update_testfile(cpursc, testfile)

    Setting.update_cfg_files(cfg, cpursc)


if __name__ == "__main__":
     main(sys.argv[0], sys.argv[1:])
