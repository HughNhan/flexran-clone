#!/usr/bin/python3
# This is based on https://gist.github.com/amadorpahim/3062277

import os,re,copy,sys,getopt,yaml
import xml.etree.ElementTree as ET

cpuinfo = '/proc/cpuinfo'
cputopology = '/sys/devices/system/cpu'
procstatus = '/proc/self/status'
l1xmldefault = '/opt/flexran/bin/nr5g/gnb/l1/phycfg_timer.xml'
l2xmldefault = '/opt/flexran/bin/nr5g/gnb/testmac/testmac_cfg.xml'

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
        cpuinfo = CpuInfo()

        # remove cpu that does not belong to cpuinfo
        for c in self.original:
            if not cpuinfo.has(c):
                self.available.remove(c)
        if not nosibling:
            return
        for c in self.available:
            siblings = cpuinfo.threadsibling(c)
            for s in siblings:
                self.available.remove(s)

    # allocate one cpu, always use low order cpu if possible
    def allocateone(self):
        try:
            cpu= self.available.pop(0)
        except IndexError:
            sys.exit("failed to allocate cpu")
        return cpu

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
    def __init__(self, cfg, l1cfgfile, l2cfgfile):
        try:
            f = open(cfg, 'r')
            self.doc = yaml.load(f)
            self.l1threads  = self.doc["L1"]["Threads"]
            print(self.l1threads)
            self.l1bbu = self.doc["L1"]["BbuPools"]
            self.l2threads = self.doc["L2"]["Threads"]
            print(self.l2threads)
            f.close()
        except:
            sys.exit("can't process %s" %(cfg))
        try:
            self.l1tree = ET.parse(l1cfgfile)
            self.l1root = self.l1tree.getroot()
        except:
            sys.exit("can't process %s" %(l1cfgfile))
        try:
            self.l2tree = ET.parse(l2cfgfile)
            self.l2root = self.l2tree.getroot()
        except:
            sys.exit("can't process %s" %(l2cfgfile))

    def _update_threads(self, rsc, root, threads):
        for l in threads:
            print(rsc.available)
            cpu = rsc.allocateone()
            for thread in l:
                overwrite = False
                if "pri" in thread:
                    overwrite = True
                    pri = thread['pri']
                for threadobj in root.iter(thread["name"]):
                    text = threadobj.text
                    # replace text with new cpu and priority
                    print("for thread %s, allocate cpu %s\n" %(thread["name"], cpu))
                    strlist = re.split(', *', text)
                    strlist[0] = str(cpu)
                    if overwrite:
                        strlist[1] = str(pri)
                    text = ",".join(strlist)
                    threadobj.text = text
        
    def update_l1threads(self, rsc):
        self._update_threads(rsc, self.l1root, self.l1threads)

    def update_l2threads(self, rsc):
        self._update_threads(rsc, self.l2root, self.l2threads)

    def update_l1bbu(self, rsc):
        for pool in self.l1bbu:
            v = 0
            try:
                bbu_threads = int(pool['threads'])
            except NameError:
                bbu_threads = 0
            for i in range(bbu_threads):
                cpu = rsc.allocate_from_range(pool['low'], pool['high'])
                if cpu is not None:
                    v ^= 1<<cpu
                else:
                    print("not enough cpu for bbu threads, use whatever available")
                    break
            hexstr = hex(v)
            for bbuobj in self.l1root.iter(pool["name"]):
                bbuobj.text = hexstr

    def update_fec(self):
        fecmode = "0"
        # the env name starts with PCIDEVICE_INTEL_COM_INTEL_FEC
        feclist = [ name for name in os.environ.keys() if "PCIDEVICE_INTEL_COM_INTEL_FEC" in name ]
        if len(feclist) > 0:
            fecmode = "1"
            # only use the first from the env
            pcinum = os.environ[feclist[0]]
            for fecobj in self.l1root.iter("dpdkBasebandDevice"):
                fecobj.text = pcinum
            for fecobj in self.l2root.iter("dpdkBasebandDevice"):
                fecobj.text = pcinum
        for modeobj in self.l1root.iter("dpdkBasebandFecMode"):
            modeobj.text = fecmode
        for modeobj in self.l2root.iter("dpdkBasebandFecMode"):
            modeobj.text = fecmode


    def writel1xml(self, l1file):
        self.l1tree.write(l1file)

    def writel2xml(self, l2file):
        self.l2tree.write(l2file)

def main(name, argv):
    l1xml = l1xmldefault
    l2xml = l2xmldefault
    writeback = False
    nosibling = False
    cfg = "threads.yaml"
    helpstr = name + " --l1xml=<l1xml-file-path>"\
                     " --l2xml=<l2xml-file-path>"\
                     " --cfg=<yaml_cfg>"\
                     " --writeback"\
                     " --nosibling"\
                     "\n"
    try:
        opts, args = getopt.getopt(argv,"h",["l1xml=","l2xml=", "cfg=", "writeback", "nosibling"])
    except getopt.GetoptError:
        print(helpstr)
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print(helpstr)
            sys.exit()
        elif opt in ("--l1xml"):
            l1xml = arg
        elif opt in ("--l2xml"):
            l2xml = arg
        elif opt in ("--cfg"):
            cfg = arg
        elif opt in ("--writeback"):
            writeback = True
        elif opt in ("--allow-sibling"):
            allow_sibling = True

    status_content = open(procstatus).read().rstrip('\n')
    cpursc = CpuResource(status_content, nosibling)
    setting = Setting(cfg, l1xml, l2xml)
    setting.update_l1threads(cpursc)
    setting.update_l2threads(cpursc)
    setting.update_l1bbu(cpursc)
    setting.update_fec()
    l1output = l1xml
    l2output = l2xml
    if not writeback:
        l1output = os.path.basename(l1xml) + '.out'
        l2output = os.path.basename(l2xml) + '.out'
    setting.writel1xml(l1output)
    setting.writel2xml(l2output)

if __name__ == "__main__":
     main(sys.argv[0], sys.argv[1:])
