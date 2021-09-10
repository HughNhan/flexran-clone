#!/usr/bin/python3
# This is based on https://gist.github.com/amadorpahim/3062277

import os,re,copy,sys,getopt,yaml
import xml.etree.ElementTree as ET

cpuinfo = '/proc/cpuinfo'
cputopology = '/sys/devices/system/cpu'
procstatus = '/proc/self/status'

def getcpulist(value):
    siblingslist = []
    for item in value.split(','):
        if '-' in item:
           subvalue = item.split('-')
           siblingslist.extend(range(int(subvalue[0]), int(subvalue[1]) + 1))
        else:
           siblingslist.extend([int(item)])
    return siblingslist

def siblings(cputopology, cpudir, siblingsfile):
    # Known core_siblings_list / thread_siblings_list  formats:
    ## 0
    ## 0-3
    ## 0,4,8,12
    ## 0-7,64-71
    value = open('/'.join([cputopology, cpudir, 'topology', siblingsfile])).read().rstrip('\n')
    return getcpulist(value)


class CpuInfo:
    def __init__(self):
        self.info = {}
        self.p = {}
        for line in open(cpuinfo):
            if line.strip() == '':
                self.p = {}
                continue
            key, value = map(str.strip, line.split(':', 1))
            if key == 'processor':
                self.info[value] = self.p
            else:
                self.p[key] = value

        self.topology = {}
        try:
            r = re.compile('^cpu[0-9]+')
            cpudirs = [f for f in os.listdir(cputopology) if r.match(f)]
            for cpudir in cpudirs:
                # skip the offline cpus
                try:
                    online = open('/'.join([cputopology, cpudir, 'online'])).read().rstrip('\n')
                    if online == '0':
                        continue
                except:
                    continue
                self.t = {}
                self.topology[cpudir] = self.t
                self.t['physical_package_id'] = open('/'.join([cputopology, cpudir, '/topology/physical_package_id'])).read().rstrip('\n')
                self.t['core_siblings_list'] = siblings(cputopology, cpudir, 'core_siblings_list')
                self.t['thread_siblings_list'] = siblings(cputopology, cpudir, 'thread_siblings_list')

        except:
            # Cleaning the topology due to error.
            # /proc/cpuinfo will be used instead.
            print("can't access /sys. Use /proc/cpuinfo")
            self.topology = {}

        self.allthreads = set()
        if self.topology:
            for p in self.topology.values():
                self.allthreads = self.allthreads.union(p['thread_siblings_list'])

    def has(self, i):
        return i in self.allthreads

    def threads(self):
        if self.topology:
            return len(set(sum([p.get('thread_siblings_list', '0') for p in self.topology.values()], [])))
        else:
            return int(self.info.itervalues().next()['siblings']) * self.sockets()

    def cores(self):
        if self.topology:
            allcores = sum([p.get('core_siblings_list', '0') for p in self.topology.values()], [])
            virtcores = sum([p.get('thread_siblings_list', '0')[1:]  for p in self.topology.values()], [])
            return len(set([item for item in allcores if item not in virtcores]))
        else:
            return int(self.info.itervalues().next()['cpu cores']) * self.sockets()

    def sockets(self):
        if self.topology:
            return len(set([p.get('physical_package_id', '0') for p in self.topology.values()]))
        else:
            return len(set([p.get('physical id', '0') for p in self.info.values()]))

    def threadsibling(self, thread):
        cpu = "cpu" + str(thread)
        siblings = copy.deepcopy(self.topology[cpu]['thread_siblings_list'])
        siblings.remove(thread)
        return siblings


class CpuResource:
    # data is the file content read from /proc/self/status; nosibling: True means do not use sibling threads
    def __init__(self, data, nosibling=False):
        try:
            cpustr = re.search(r'Cpus_allowed_list:\s*([0-9\-\,]+)', data).group(1)
        except:
            sys.exit("couldn't match Cpus_allowed_list")
        self.original = getcpulist(cpustr)
        self.available = copy.deepcopy(self.original)
        self.cpuinfo = CpuInfo()

        # remove cpu that does not belong to cpuinfo
        for c in self.original:
            if not self.cpuinfo.has(c):
                self.available.remove(c)
        if not nosibling:
            return
        for c in self.available:
            siblings = self.cpuinfo.threadsibling(c)
            for s in siblings:
                self.available.remove(s)

    # allocate one cpu, always use low order cpu if possible
    def allocateone(self):
        try:
            cpu= self.available.pop(0)
        except IndexError:
            sys.exit("failed to allocate cpu")
        return cpu

    # allocate one thread, and remove its sibling thread from available list
    def allocate_whole_core(self):
        cpu = self.allocateone()
        siblings = self.cpuinfo.threadsibling(cpu)
        for s in siblings:
            self.available.remove(s)
        return cpu

    def allocate_siblings(self, num):
        cpus = []
        while (num > 0):
            cpu = self.allocateone()
            cpus.append(cpu)
            num -= 1
            if (num == 0):
                break
            siblings = self.cpuinfo.threadsibling(cpu)
            for s in siblings:
                if s in self.available:
                    self.available.remove(s)
                    cpus.append(s)
                    num -= 1
        return cpus

    # specify the list of cpu to remove from available list
    def remove(self, l):
        self.available.remove(l)

    def allocate_from_range(self, low, high):
        p = None
        for i in self.available:
            if i<=high and i>=low:
                p = i
                break
        if p is not None:
            self.available.remove(p)
        return p

    # allocate num of cpus
    def allocate(self, num):
        cpus = []
        for i in range(num):
            cpus.append(self.allocateone())
        return cpus

class Setting:
    def __init__(self, cfg):
        try:
            f = open(cfg, 'r')
            self.cfg = list(f)
            f.close()
        except:
            sys.exit("can't process %s" %(cfg))

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            print('exit')
            self.f.close()
        except:
            sys.exit("can't close %s" %(f))

    def update_cfg_files(self):
    # use self.cfg info to update the config files: phycfg_timer.xml, testmac_cfg.xml
    # assume these config files exist under the current directory
    # reference https://docs.google.com/document/d/1CLlfh2pt2eOxwus0gnOXuAnGT9yRYVu0Rrr8wTAP_0I/edit?usp=sharing
        pass

    # A function to take the setcore maps in the config file and allocate
    # relevant cpus on the current machine, creating a new map and writing it
    # in place, always allocating siblings.
    #
    # References:
    #   https://stackoverflow.com/questions/38935169/convert-elements-of-a-list-into-binary
    #   https://stackoverflow.com/questions/21409461/binary-list-from-indices-of-ascending-integer-list
    def update_testfile(self, rsc, testfile):
        line_index = 0
        for line in self.cfg:
            if 'setcore' in line:
                setcore_index = line.index('setcore')
                # The number of cpus (cores or threads, depening on hyperthreading, needed.)
                # Take the string, convert to hex, convert to binary, count the 1s.
                num_cpus = (bin(int(line[setcore_index + len('setcore'):].strip(), 16))[2:]).count('1')
                print(num_cpus)
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
                self.cfg[line_index] = line.replace(line[setcore_index + len('setcore'):], new_setcore_hex)

            line_index += 1

        # Write the new configuration to the same file.
        f = open(testfile, 'w')
        f.writelines(self.cfg)
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
        setting = Setting(testfile)
        setting.update_testfile(cpursc, testfile)

if __name__ == "__main__":
     main(sys.argv[0], sys.argv[1:])
