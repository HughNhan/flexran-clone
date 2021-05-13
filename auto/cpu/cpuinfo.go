package main

import (
	"flag"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"regexp"

	"github.com/antchfx/xmlquery"
	//"github.com/go-xmlfmt/xmlfmt"
	"github.com/google/cadvisor/fs"
	"github.com/google/cadvisor/machine"
	"github.com/google/cadvisor/utils/sysfs"
	"k8s.io/klog/v2"
)

/* parse file such as /proc/self/status to get linux style cpuset string
 */
func getAllowedCpus(fileName string) (string, error) {
	status, err := ioutil.ReadFile(fileName)
	if err != nil {
		return "", err
	}
	r, _ := regexp.Compile(`Cpus_allowed_list:\s+([0-9\-\,]+)`)
	return r.FindStringSubmatch(string(status))[1], nil
}

const (
	procStatusPath   = "/proc/self/status"
	l1XmlPathDefault = "/opt/flexran/bin/nr5g/gnb/l1/phycfg_timer.xml"
	l2XmlPathDefault = "/opt/flexran/bin/nr5g/gnb/testmac/testmac_cfg.xml"
)

var (
	// threads in the same array share cpu
	l1Threads = [][]string{{"systemThread"}, {"timerThread", "radioDpdkMaster"}, {"FpgaDriverCpuInfo", "FrontHaulCpuInfo"}}
	l2Threads = [][]string{{"wlsRxThread"}, {"systemThread", "runThread"}, {"urllcThread"}}
)

type bbuPool struct {
	name string
	low  int
	high int
}

var l1bbuPool = []bbuPool{
	{name: "BbuPoolThreadDefault_0_63", low: 0, high: 63},
	{name: "BbuPoolThreadDefault_64_127", low: 64, high: 127},
}

func NewCpuBitMap(allowSibling bool, statusFile string) *Bitmap {
	sysFs := sysfs.NewRealSysFs()
	context := fs.Context{}
	fsInfo, err := fs.NewFsInfo(context)
	inHostNamespace := false
	if _, err := os.Stat("/rootfs/proc"); os.IsNotExist(err) {
		inHostNamespace = true
	}
	machineInfo, err := machine.Info(sysFs, fsInfo, inHostNamespace)
	if err != nil {
		klog.ErrorS(err, "Failed to get machineInfo")
		//fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(1)
	}

	allowCpuStr, err := getAllowedCpus(statusFile)
	if err != nil {
		klog.ErrorS(err, "Failed to parse allowed cpu list from file", "file", statusFile)
		os.Exit(1)
	}
	bitmap, err := ParseCPUStr(allowCpuStr)
	if err != nil {
		klog.ErrorS(err, "Failed to get bitmap from cpu string", "cpustr", allowCpuStr)
		os.Exit(1)
	}

	if allowSibling == false {
		// remove silbling CPU from the list
		for _, node := range machineInfo.Topology {
			for _, core := range node.Cores {
				deleteMode := false
				for _, threadID := range core.Threads {
					if bitmap.IsSet(threadID) {
						if deleteMode == false {
							// only allow one thread from each core (thread group)
							deleteMode = true
						} else {
							bitmap.Clear(threadID)
						}
					}
				}
			}
		}
	}
	return bitmap
}

// allocate num of cpus
func (bitmap *Bitmap) AllocateCpu(num int) []int {
	var cpuList []int
	for num > 0 {
		nextBit, err := bitmap.FindAndClear()
		if err != nil {
			klog.ErrorS(err, "Failed to find availble cpu", "bitmap", bitmap.String())
			os.Exit(1)
		}
		cpuList = append(cpuList, nextBit)
		num -= 1
	}
	return cpuList
}

func (bitmap *Bitmap) AllocateCpuHexStr(num int) string {
	var bits Bitmap
	cpuList := bitmap.AllocateCpu(num)
	for _, i := range cpuList {
		bits.Set(i)
	}
	return bits.String()
}

func updateXmlTheads(doc *xmlquery.Node, thread string, cpu int, re *regexp.Regexp) {
	xpath := "//Threads/" + thread + "[1]"
	threadObj := xmlquery.FindOne(doc, xpath)
	currText := threadObj.InnerText()
	rightPart := re.FindString(currText)
	fixText := fmt.Sprint(cpu) + "," + rightPart
	threadObj.UpdateInnerText(fixText)
}

func main() {
	l1XmlPathPtr := flag.String("l1cfg", l1XmlPathDefault, "l1 xml config path")
	l2XmlPathPtr := flag.String("l2cfg", l2XmlPathDefault, "l2 xml config path")
	boolPtr := flag.Bool("use-silbing-thread", false, "use sibling thread on the same core")
	writebackPtr := flag.Bool("write-back", false, "write back to the xml config files")

	flag.Parse()

	cpuBitMap := NewCpuBitMap(*boolPtr, procStatusPath)

	l1XmlFile := *l1XmlPathPtr
	l2XmlFile := *l2XmlPathPtr
	fl1, err := os.Open(l1XmlFile)
	if err != nil {
		panic(err)
	}
	defer fl1.Close()

	l1doc, err := xmlquery.Parse(fl1)
	if err != nil {
		panic(err)
	}

	// example: 3, 96, 0
	re := regexp.MustCompile("\\s*\\d+,\\s*\\d+\\s*$")

	for _, threads := range l1Threads {
		cpu := cpuBitMap.AllocateCpu(1)[0]
		for _, thread := range threads {
			updateXmlTheads(l1doc, thread, cpu, re)
		}
	}

	fl2, err := os.Open(l2XmlFile)
	if err != nil {
		panic(err)
	}
	defer fl2.Close()

	l2doc, err := xmlquery.Parse(fl2)
	if err != nil {
		panic(err)
	}
	for _, threads := range l2Threads {
		cpu := cpuBitMap.AllocateCpu(1)[0]
		for _, thread := range threads {
			updateXmlTheads(l2doc, thread, cpu, re)
		}
	}

	// lastly, take care of l1 bbupool with left over cpu
	for _, pool := range l1bbuPool {
		bbuHexStr := cpuBitMap.CopyBitMap(pool.low, pool.high).String()
		xpath := "//" + pool.name
		threadObj := xmlquery.FindOne(l1doc, xpath)
		threadObj.UpdateInnerText(bbuHexStr)
	}

	var ofl1, ofl2 *os.File
	if *writebackPtr == false {
		// write to .out under current directory
		l1XmlFile = filepath.Base(l1XmlFile) + ".out"
		ofl1, err = os.Create(l1XmlFile)
		if err != nil {
			panic(err)
		}

		l2XmlFile = filepath.Base(l2XmlFile) + ".out"
		ofl2, err = os.Create(l2XmlFile)
		if err != nil {
			panic(err)
		}
	} else {
		ofl1, err = os.OpenFile(l1XmlFile, os.O_RDWR, 0777)
		if err != nil {
			panic(err)
		}
		ofl2, err = os.OpenFile(l2XmlFile, os.O_RDWR, 0777)
		if err != nil {
			panic(err)
		}
	}

	defer ofl1.Close()
	defer ofl2.Close()

	//ofl1.WriteString(xmlfmt.FormatXML(l1doc.OutputXML(false), "", "  "))
	ofl1.WriteString(l1doc.OutputXML(false))
	ofl1.Sync()

	ofl2.WriteString(l2doc.OutputXML(false))
	ofl2.Sync()

}
