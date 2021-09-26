# Run FlexRAN test suites in OpenShift 

## Compile flexran

The following steps prove to work on fresh installed RHEL8.2

```
subscription-manager register
subscription-manager attach --auto
subscription-manager repos --enable codeready-builder-for-rhel-8-x86_64-rpms
yum groupinstall -y 'Development Tools'
yum install -y git patch tar zip unzip python3 cmake3 libstdc++-static elfutils-libelf-devel zlib-devel numactl-devel libhugetlbfs-devel
pip3 install meson && pip3 install ninja
mkdir -p /opt && cd /opt && git clone git://dpdk.org/dpdk-stable dpdk
cd /opt/dpdk && git checkout 20.11 && patch -p1 <  dpdk_20.11_20.11.5.patch
cd /opt && tar zxvf system_studio_2019_update_5_ultimate_edition.tar.gz
cd /opt/system_studio_2019_update_5_ultimate_edition && sed -i -r -e 's/^ACCEPT_EULA=.*/ACCEPT_EULA=accept/' -e 's/^ACTIVATION_TYPE=.*/ACTIVATION_TYPE=license_file/' -e 's%^#?ACTIVATION_LICENSE_FILE=.*%ACTIVATION_LICENSE_FILE=/opt/flexran_license.lic%' silent.cfg
cd /opt/system_studio_2019_update_5_ultimate_edition && ./install.sh -s silent.cfg
cd /opt && mkdir -p flexran && tar zxvf FlexRAN-20.11.tar.gz -C flexran/
cd /opt/flexran && ./extract.sh 
cd /opt && unzip -d flexran FlexRAN-20.11.6_update.zip
cd /opt/flexran && patch -p1 < FlexRAN-20.11.6_update.patch
cd /opt/flexran && source ./set_env_var.sh -d
sed -r -i -e 's%^#include <linux/bootmem.h>%//#include <linux/bootmem.h>%' /opt/flexran/libs/cpa/sub6/rec/drv/src/nr_dev.c
cd /opt/flexran && ./flexran_build.sh -e -r 5gnr_sub6 -b -m sdk 
cd /opt/dpdk && meson build
cd /opt/dpdk/build && meson configure -Dflexran_sdk=/opt/flexran/sdk/build-avx512-icc/install && ninja
export MESON_BUILD=1
cd /opt/flexran && ./flexran_build.sh -e -r 5gnr_sub6 -b
```

## Build container image

```
sh flexran-container.sh
```

The script will build a container image "flexran".

 
## Verify flexran container image using podman

```podman run --name flexran -d --privileged --cpuset-cpus 4,6,8,10,12,14,16,18 --mount 'type=bind,src=/sys,dst=/sys' --mount 'type=bind,src=/dev,destination=/dev' flexran sleep infinity```

From terminal 1, run ```podman exec -it flexran sh```. To run test suites in timer mode, the entry point for l1app is /opt/flexran/bin/nr5g/gnb/l1/l1.sh. This script will drop into the PHY console. Before running this script, one must update the settings in phycfg_timer.xml. The following xml fields need to be updated,
* DPDK/dpdkBasebandFecMode
* DPDK/dpdkBasebandDevice
* Threads/{systemThread,timerThread}

There are comments in the xml file to explain the purpose of these fields.  

From terminal 2, run ```podman exec -it flexran sh```. The entry point for testmac is /opt/flexran/bin/nr5g/gnb/testmac/l2.sh. This script will drop into the testmac console. Before running this script, one must update the settings in testmac_cfg.xml. The following xml fields need to be updated,
* Threads/{wlsRxThread,systemThread,runThread}

There are comments in the xml file to explain the purpose of these fields.

To start the actual test, in the testmac console, `runall 0`


## OpenShift FlexRAN test topology

![test topology](https://docs.google.com/drawings/d/e/2PACX-1vRWU499sFr2jgnzafd8NlSMGo-eHWDef9fzB6Ivzme-6KAsLZvC3ckBgCzA7nV-YlZJcLRMdCWOsW5e/pub?w=960&h=720)

## add labels to the worker node

```
oc label --overwrite node worker1 node-role.kubernetes.io/worker-cnf=""
oc label --overwrite node worker1 feature.node.kubernetes.io/network-sriov.capable=true
oc label node worker1 fpga.intel.com/intel-accelerator-present=""
```

## Install performance-addon operator

```
cat <<EOF  | oc create -f -
apiVersion: v1
kind: Namespace
metadata:
  labels:
    openshift.io/run-level: "1" 
  name: openshift-performance-addon
---
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: openshift-performance-addon-operator
  namespace: openshift-performance-addon
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: performance-addon-operator
  namespace: openshift-performance-addon
spec:
  channel: "${OCP_CHANNEL_NUM}"
  name: performance-addon-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF

while ! oc get pods -n openshift-performance-addon | grep Running; do
    echo "waiting for performance-addon operator online"
    sleep 5
done

cat <<EOF  | oc create -f -
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfigPool
metadata:
  name: worker-cnf
  namespace: openshift-machine-config-operator
  labels:
    machineconfiguration.openshift.io/role: worker-cnf
spec:
  paused: false 
  machineConfigSelector:
    matchExpressions:
      - key: machineconfiguration.openshift.io/role
        operator: In
        values: [worker,worker-cnf]
  nodeSelector:
    matchLabels:
      node-role.kubernetes.io/worker-cnf: ""
EOF

cat <<EOF  | oc create -f -
apiVersion: performance.openshift.io/v1alpha1
kind: PerformanceProfile
metadata:
  name: cnv-sriov-profile 
spec:
  cpu:
    isolated: "4-39"
    reserved: "0-3"
  hugepages:
    defaultHugepagesSize: "1G"
    pages:
    - size: "1G"
      count: 16 
  realTimeKernel:
    enabled: true 
  nodeSelector:
    node-role.kubernetes.io/worker-cnf: "" 
EOF

status=$(oc get mcp | awk '/worker-cnf/{print $4}')
while [[ $status != "False" ]]; do 
    echo "waiting for mcp complete"
    sleep 5
    status=$(oc get mcp | awk '/worker-cnf/{print $4}')
done
```

## install N3000 programming operator

```
oc new-project vran-acceleration-operators

cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: n3000-operators
  namespace: vran-acceleration-operators
spec:
  targetNamespaces:
    - vran-acceleration-operators
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: n3000-subscription
  namespace: vran-acceleration-operators 
spec:
  channel: stable
  name: n3000
  source: certified-operators
  sourceNamespace: openshift-marketplace
EOF

# matching: OpenNESS Operator for Intel® FPGA PAC N3000
while ! oc get csv -n vran-acceleration-operators | grep 'FPGA PAC N3000'; do
    echo "wait for N3000 programming operator online"
    sleep 5
done
```

## Flash N3000 with 5G image

```
cat <<EOF | oc apply -f -
apiVersion: fpga.intel.com/v1
kind: N3000Cluster
metadata:
  name: n3000
  namespace: vran-acceleration-operators
spec:
  nodes:
    - nodeName: "worker1"
      fpga:
        - userImageURL: "http://192.168.222.1:81/bin/20ww43.5-2x2x25G-5GLDPC-v1.6.2-3.0.1-unsigned.bin"
          PCIAddr: "0000:61:00.0"
          checksum: "cab45415c418615d005dd587f4f11e9a"
EOF

# node status should change to progress
oc get n3000node

# wait for it to complete
while oc get n3000node | grep InProgress
    echo "flashing in progress"
    sleep 5
done
```

## Install wireless FEC operator

```
if ! oc get ns | grep vran-acceleration-operators; then
    oc new-project vran-acceleration-operators
fi

cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: vran-operators
  namespace: vran-acceleration-operators
spec:
  targetNamespaces:
    - vran-acceleration-operators
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: sriov-fec-subscription
  namespace: vran-acceleration-operators
spec:
  channel: stable
  name: sriov-fec
  source: certified-operators
  sourceNamespace: openshift-marketplace
EOF

# matching: OpenNESS SR-IOV Operator for Wireless FEC Accelerators
while ! oc get csv -n vran-acceleration-operators | grep 'Wireless FEC'; do
    echo "wait for Wireless FEC operator online"
    sleep 5
done
```

## Create FEC VFs on N3000

```
cat <<EOF | oc apply -f -
apiVersion: sriovfec.intel.com/v1
kind: SriovFecClusterConfig
metadata:
  name: config
  namespace: vran-acceleration-operators
spec:
  nodes:
    - nodeName: worker1 
      physicalFunctions:
        - pciAddress: 0000:66:00.0 
          pfDriver: pci-pf-stub
          vfDriver: vfio-pci
          vfAmount: 2
          bbDevConfig:
            n3000:
              # Network Type: either "FPGA_5GNR" or "FPGA_LTE"
              networkType: "FPGA_5GNR"
              # Programming mode: 0 = VF Programming, 1 = PF Programming
              pfMode: false
              flrTimeout: 610
              downlink:
                bandwidth: 3
                loadBalance: 128
                queues:
                  vf0: 16 
                  vf1: 16 
                  vf2: 0
                  vf3: 0
                  vf4: 0
                  vf5: 0
                  vf6: 0
                  vf7: 0
              uplink:
                bandwidth: 3
                loadBalance: 128
                queues:
                  vf0: 16 
                  vf1: 16 
                  vf2: 0
                  vf3: 0
                  vf4: 0
                  vf5: 0
                  vf6: 0
                  vf7: 0
EOF

# matching: worker1   Succeeded
while oc get sriovfecnodeconfigs -n vran-acceleration-operators | grep Succeeded; do
    echo "waiting for sriovfecnodeconfigs succeeded"
    sleep 5
done

# make sure intel.com/intel_fec_5g show up
oc get node worker1 -o json | jq -r '.status.capacity' 
```

## Create FEC VFs on ACC100

```
cat <<EOF  | oc create -f -
apiVersion: sriovfec.intel.com/v1
kind: SriovFecClusterConfig
metadata:
  name: config
  namespace: vran-acceleration-operators
spec:
  nodes:
    - nodeName: worker1
      physicalFunctions:
        - pciAddress: 0000:b5:00.0
          pfDriver: pci-pf-stub
          vfDriver: vfio-pci
          vfAmount: 16
          bbDevConfig:
            acc100:
              pfMode: false
              numVfBundles: 16
              maxQueueSize: 1024
              uplink4G:
                numQueueGroups: 0
                numAqsPerGroups: 16
                aqDepthLog2: 4
              downlink4G:
                numQueueGroups: 0
                numAqsPerGroups: 16
                aqDepthLog2: 4
              uplink5G:
                numQueueGroups: 4
                numAqsPerGroups: 16
                aqDepthLog2: 4
              downlink5G:
                numQueueGroups: 4
                numAqsPerGroups: 16
                aqDepthLog2: 4
EOF

# matching: worker1   Succeeded
while oc get sriovfecnodeconfigs -n vran-acceleration-operators | grep Succeeded; do
    echo "waiting for sriovfecnodeconfigs succeeded"
    sleep 5
done

# make sure intel.com/intel_fec_acc100 show up
oc get node worker1 -o json | jq -r '.status.capacity' 
```

## Run flexran timer test suite from Openshift with software FEC

```
cat <<EOF  | oc create -f -
apiVersion: v1 
kind: Pod 
metadata:
  name: flexran
spec:
  restartPolicy: Never
  containers:
  - name: flexran 
    image: 192.168.222.1:5000/flexran 
    imagePullPolicy: Always 
    command:
      - sleep
      - "36000" 
    securityContext:
      privileged: true
    volumeMounts:
    - mountPath: /dev/hugepages
      name: hugepage
    - mountPath: /sys
      name: sys
    resources:
      limits:
        hugepages-1Gi: 16Gi
        memory: 16Gi
        cpu: 8
      requests:
        hugepages-1Gi: 16Gi
        memory: 16Gi
        cpu: 8
  volumes:
  - name: hugepage
    emptyDir:
      medium: HugePages
  - name: sys
    hostPath:
      path: /sys
  nodeSelector:
    node-role.kubernetes.io/worker-cnf: ""
EOF
```

From terminal 1, run ```oc exec -it flexran sh```. To run test suites in timer mode, the entry point for l1app is /opt/flexran/bin/nr5g/gnb/l1/l1.sh. This script will drop into the PHY console. Before running this script, one must update the settings in phycfg_timer.xml. The following xml fields need to be updated,
* DPDK/dpdkBasebandFecMode
* DPDK/dpdkBasebandDevice
* Threads/{systemThread,timerThread}

There are comments in the xml file to explain the purpose of these fields.  

From terminal 2, run ```oc exec -it flexran sh```. The entry point for testmac is /opt/flexran/bin/nr5g/gnb/testmac/l2.sh. This script will drop into the testmac console. Before running this script, one must update the settings in testmac_cfg.xml. The following xml fields need to be updated,
* Threads/{wlsRxThread,systemThread,runThread}

There are comments in the xml file to explain the purpose of these fields.

To start the actual test, in the testmac console, `runall 0`


## Run flexran timer test suite from Openshift with FEC hardware acceleration

```
cat <<EOF  | oc create -f -
apiVersion: v1 
kind: Pod 
metadata:
  name: flexran
spec:
  restartPolicy: Never
  containers:
  - name: flexran 
    image: 10.16.231.128:5000/flexran 
    imagePullPolicy: Always 
    command:
      - sleep
      - "36000" 
    securityContext:
      privileged: true
    volumeMounts:
    - mountPath: /dev/hugepages
      name: hugepage
    - mountPath: /sys
      name: sys
    - name: varrun
      mountPath: /var/run/dpdk
    resources:
      limits:
        hugepages-1Gi: 16Gi
        memory: 16Gi
        cpu: 8 
        intel.com/intel_fec_5g: '1'
      requests:
        hugepages-1Gi: 16Gi
        memory: 16Gi
        cpu: 8
        intel.com/intel_fec_5g: '1'
  volumes:
  - name: hugepage
    emptyDir:
      medium: HugePages
  - name: sys
    hostPath:
      path: /sys
  - name: varrun
    emptyDir: {}
  nodeSelector:
    node-role.kubernetes.io/worker-cnf: ""
EOF
```

To use acc100, replace intel_fec_5g with intel_fec_acc100 in the above yaml.

Once the pod is started, modify the config xml files and run l1.sh and l2.sh as illustrated earlier. 


## Run xran test suite from Openshift with FEC hardware acceleration

In addition to enabling the operators mentioned in the timer mode testing, the following additional steps are required.

### Disable chronyd

```
cat <<EOF  | oc create -f -
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  labels:
    # Pay attention to the node label, create MCP accordingly
    machineconfiguration.openshift.io/role: worker-cnf
  name: disable-chronyd
spec:
  config:
    ignition:
      version: 2.2.0
    systemd:
      units:
        - contents: |
            [Unit]
            Description=NTP client/server
            Documentation=man:chronyd(8) man:chrony.conf(5)
            After=ntpdate.service sntp.service ntpd.service
            Conflicts=ntpd.service systemd-timesyncd.service
            ConditionCapability=CAP_SYS_TIME

            [Service]
            Type=forking
            PIDFile=/run/chrony/chronyd.pid
            EnvironmentFile=-/etc/sysconfig/chronyd
            ExecStart=/usr/sbin/chronyd $OPTIONS
            ExecStartPost=/usr/libexec/chrony-helper update-daemon
            PrivateTmp=yes
            ProtectHome=yes
            ProtectSystem=full

            [Install]
            WantedBy=multi-user.target
          enabled: false
          name: "chronyd.service"
EOF
```

### Enable ptp

```
cat <<EOF  | oc create -f -
---
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-ptp
  labels:
    name: openshift-ptp
    openshift.io/cluster-monitoring: "true"
---
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: ptp-operators
  namespace: openshift-ptp
spec:
  targetNamespaces:
  - openshift-ptp
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: ptp-operator-subscription
  namespace: openshift-ptp
spec:
  channel: "${OCP_CHANNEL_NUM}"
  name: ptp-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF

while ! oc get pods -n openshift-ptp | grep Running; do
    echo 'waiting for ptp pods ...'
    sleep 5
done

cat <<EOF  | oc create -f -
apiVersion: ptp.openshift.io/v1
kind: PtpConfig
metadata:
  name: ptp-cfg
  namespace: openshift-ptp
spec:
  profile:
  - interface: ens3f1
    name: profile1
    phc2sysOpts: -a -r
    ptp4lOpts: -s -2 -m
  recommend:
  - match:
    - nodeLabel: node-role.kubernetes.io/worker-cnf
    priority: 10
    profile: profile1
EOF
```

Check PTP status and make sure it is synced to the grand master, for example,
```
oc logs linuxptp-daemon-48qz2 -n openshift-ptp -c linuxptp-daemon-container
ptp4l[203555.162]: rms    6 max    8 freq   -128 +/-   5 delay  1507 +/-   0
phc2sys[203555.677]: CLOCK_REALTIME rms    5 max    5 freq  +6744 +/-   0 delay   502 +/-   0
phc2sys[203556.677]: CLOCK_REALTIME rms    8 max    8 freq  +6733 +/-   0 delay   503 +/-   0
ptp4l[203557.162]: rms    2 max    3 freq   -130 +/-   2 delay  1507 +/-   0
phc2sys[203557.677]: CLOCK_REALTIME rms    1 max    1 freq  +6737 +/-   0 delay   575 +/-   0
phc2sys[203558.678]: CLOCK_REALTIME rms    1 max    1 freq  +6737 +/-   0 delay   578 +/-   0
ptp4l[203559.163]: rms    2 max    3 freq   -132 +/-   1 delay  1507 +/-   0
phc2sys[203559.678]: CLOCK_REALTIME rms    2 max    2 freq  +6736 +/-   0 delay   573 +/-   0
```

### Create SRIOV VFs on front haul link

```
cat <<EOF  | oc create -f -
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-sriov-network-operator
  labels:
    openshift.io/run-level: "1"
---
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: sriov-network-operators
  namespace: openshift-sriov-network-operator
spec:
  targetNamespaces:
  - openshift-sriov-network-operator
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: sriov-network-operator-subsription
  namespace: openshift-sriov-network-operator
spec:
  channel: "${OCP_CHANNEL_NUM}"
  name: sriov-network-operator
  source: redhat-operators 
  sourceNamespace: openshift-marketplace
EOF

while ! oc get pods -n openshift-sriov-network-operator | grep Running; do
    echo 'waiting for sriov pods ...'
    sleep 5
done

cat <<EOF  | oc create -f -
apiVersion: sriovnetwork.openshift.io/v1
kind: SriovNetworkNodePolicy
metadata:
  name: policy-intel-west
  namespace: openshift-sriov-network-operator
spec:
  deviceType: netdevice
  mtu: 9000
  nicSelector:
    deviceID: "158b"
    rootDevices:
    - "0000:65:00.0"
    - "0000:87:00.0"
    vendor: "8086"
    pfNames:
    - ens1f0
    - ens7f0 
  nodeSelector:
    feature.node.kubernetes.io/network-sriov.capable: "true"
  numVfs: 8
  priority: 5
  resourceName: intelnics0
EOF

cat <<EOF  | oc create -f -
apiVersion: sriovnetwork.openshift.io/v1
kind: SriovNetwork
metadata:
  name: sriov-vlan10
  namespace: openshift-sriov-network-operator
spec:
  ipam: "" 
  resourceName: intelnics0
  vlan: 10
  networkNamespace: default
---
apiVersion: sriovnetwork.openshift.io/v1
kind: SriovNetwork
metadata:
  name: sriov-vlan20
  namespace: openshift-sriov-network-operator
spec:
  ipam: "" 
  resourceName: intelnics0
  vlan: 20
  networkNamespace: default
EOF
```

### Run flexran test pod with FEC hardware acceleration

```
cat <<EOF  | oc create -f -
apiVersion: v1 
kind: Pod 
metadata:
  name: flexran-du
  annotations:
    k8s.v1.cni.cncf.io/networks: sriov-vlan10,sriov-vlan20
spec:
  restartPolicy: Never
  containers:
  - name: flexran-du 
    image: 10.16.231.128:5000/flexran 
    imagePullPolicy: Always 
    command:
      - sleep
      - "36000" 
    securityContext:
      privileged: true
    volumeMounts:
    - mountPath: /dev/hugepages
      name: hugepage
    - mountPath: /sys
      name: sys
    - name: varrun
      mountPath: /var/run/dpdk
    resources:
      limits:
        hugepages-1Gi: 16Gi
        memory: 16Gi
        cpu: 8 
        intel.com/intel_fec_acc100: '1'
      requests:
        hugepages-1Gi: 16Gi
        memory: 16Gi
        cpu: 8
        intel.com/intel_fec_acc100: '1'
  volumes:
  - name: hugepage
    emptyDir:
      medium: HugePages
  - name: sys
    hostPath:
      path: /sys
  - name: varrun
    emptyDir: {}
  nodeSelector:
    node-role.kubernetes.io/worker-cnf: ""
EOF
```

### Simulate RU 

On the RU server (the server on the right in the topology diagram), create 2 VFs,
```
echo 2 > /sys/class/net/${RU_ETH}/device/sriov_numvfs
ip link set dev ${RU_ETH} vf 0 vlan 10 mac 00:11:22:33:00:01 spoofchk off
ip link set dev ${RU_ETH} vf 1 vlan 20 mac 00:11:22:33:00:11 spoofchk off 
```

Go to directory /opt/flexran/bin/nr5g/gnb/l1/orancfg/sub3_mu0_20mhz_4x4/oru and make following changes.

In run_o_ru.sh, update --vf_addr_o_xu_a with the pci address of the two VF created.

In usecase_ru.cfg, 
* ioCore
* ioWorker
* oXuRem0Mac0, oXuRem0Mac1: DU's VF mac address

In config_file_o_ru.dat,
* duMac0, duMac1: DU's VF mac address

To start the RU,
```
cd /opt/flexran && source ./set_env_var.sh -d
cd bin/nr5g/gnb/l1/orancfg/sub3_mu0_20mhz_4x4/oru
./run_o_ru.sh
```

### Run xran test suite from the flexran pod

After the pod is started, on terminal 1 run ```oc exec -it flextan sh```. Go to directory /opt/flexran/bin/nr5g/gnb/l1/orancfg/sub3_mu0_20mhz_4x4/gnb/ and update phycfg_xran.xml and xrancfg_sub6_oru.xml as illustrated below.

In phycfg_xran.xml, the following fields need to be updated:
* DPDK/dpdkBasebandFecMode: 1 if using HW FEC
* DPDK/dpdkBasebandDevice: HW FEC pci address based on value of env var PCIDEVICE_INTEL_COM_INTEL_FEC_ACC100
* Threads: same rule as phycfg_timer.xml applies

In xrancfg_sub6_oru.xml, the following fields need to be updated:
* PciBusAddoRu0Vf0,PciBusAddoRu0Vf1: SRIOV VF pci address based on value of env var PCIDEVICE_OPENSHIFT_IO_INTELNICS0
* oRuRem0Mac0, oRuRem0Mac1: remote RU's corresponding VF mac address
* xRANThread: allocate a new cpu thread and put down the cpu id
* xRANWorker: allocate a new cpu thread and put down the cpu mask

Go to directory /opt/flexran/bin/nr5g/gnb/testmac, update testmac_cfg.xml as illustrated below.

In testmac_cfg.xml, the following fields need to be updated:
* Threads: same rule as testmac_cfg.xml for timer mode

copy /opt/flexran/bin/nr5g/gnb/l1/orancfg/sub3_mu0_20mhz_4x4/gnb/testmac_clxsp_mu0_20mhz_hton_oru.cfg to /opt/flexran/bin/nr5g/gnb/testmac, and update this file:
* phystart: 4 0 100007
* setcore

After these change are made, start the l1app by 
```
source /opt/flexran/auto/env.src
/opt/flexran/auto/driver.sh vfio  # this will make sure the driver is vfio bound
cd /opt/flexran/bin/nr5g/gnb/l1/orancfg/sub3_mu0_20mhz_4x4/gnb/
./l1.sh -oru
```

on terminal 2 run ```oc exec -it flexran sh```. Start the TESTMAC by 
```
cd /opt/flexran/bin/nr5g/gnb/testmac
source /opt/flexran/auto/env.src
./l2.sh --testfile=testmac_clxsp_mu0_20mhz_hton_oru.cfg
``` 

This will automatically start the test suite.

## Simulate RU from baremetal machine

On the RU server, go to directory bin/nr5g/gnb/l1/orancfg/sub3_mu0_20mhz_4x4/oru and make following changes.

In run_o_ru.sh, update --vf_addr_o_xu_a with the pci address of the two VF created.

In usecase_ru.cfg, 
* ioCore
* ioWorker
* oXuNum: 1
* oXuLinesNumber: 1
* oXuRem0Mac0, oXuRem0Mac1: DU's VF mac address

In config_file_o_ru.dat,
* ccNum: 1
* duMac0, duMac1: DU's VF mac address
* c_plane_vlan_tag: 10
* u_plane_vlan_tag: 20

To start the RU,
```
cd bin/nr5g/gnb/l1/orancfg/sub3_mu0_20mhz_4x4/oru
./run_o_ru.sh
```

## Run front haul test from the flexran pod

After the pod is started, on terminal 1 run ```oc exec -it flextan sh```. Go to directory /opt/flexran/bin/nr5g/gnb/l1/orancfg/sub3_mu0_20mhz_4x4/gnb/ and update phycfg_xran.xml and xrancfg_sub6_oru.xml as illustrated below.

In phycfg_xran.xml, the following fields need to be updated:
* DPDK/dpdkBasebandFecMode: 1 if using HW FEC
* DPDK/dpdkBasebandDevice: HW FEC pci address based on value of env var PCIDEVICE_INTEL_COM_INTEL_FEC_ACC100
* Threads: same rule as phycfg_timer.xml applies

In xrancfg_sub6_oru.xml, the following fields need to be updated:
* oRuNum: 1
* oRuLinesNumber: 1
* PciBusAddoRu0Vf0,PciBusAddoRu0Vf1: SRIOV VF pci address based on value of env var PCIDEVICE_OPENSHIFT_IO_INTELNICS0
* oRuRem0Mac0, oRuRem0Mac1: remote RU's corresponding VF mac address
* oRu0NumCc: 1
* xRANThread: allocate a new cpu thread and put down the cpu id
* xRANWorker: allocate a new cpu thread and put down the cpu mask
* c_plane_vlan_tag: 10
* u_plane_vlan_tag: 20

Go to directory /opt/flexran/bin/nr5g/gnb/testmac, update phycfg_xran.xml as illustrated below.

In phycfg_xran.xml, the following fields need to be updated:
* Threads: same rule as testmac_cfg.xml for timer mode

copy ../bin/nr5g/gnb/l1/orancfg/sub3_mu0_20mhz_4x4/gnb/testmac_clxsp_mu0_20mhz_hton_oru.cfg to /opt/flexran/bin/nr5g/gnb/testmac, and update this file:
* phystart: 4 0 100007
* setcore

After these change are made, go to directory /opt/flexran/bin/nr5g/gnb/l1/orancfg/sub3_mu0_20mhz_4x4/gnb/ and start the l1app by `l1.sh -oru`

on terminal 2 run ```oc exec -it flexran sh```. Go to directory /opt/flexran/bin/nr5g/gnb/testmac. Start the TESTMAC by ```./l2.sh --testfile=testmac_clxsp_mu0_20mhz_hton_oru.cfg```. This will automatically start the test suite.
