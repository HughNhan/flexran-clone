# Build flexran container image

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
export RTE_SDK=/opt/dpdk
cd /opt/flexran && ./flexran_build.sh -e -r 5gnr_sub6 -b -m sdk 
cd /opt/dpdk && meson build
cd /opt/dpdk/build && meson configure -Dflexran_sdk=/opt/flexran/sdk/build-avx512-icc/install && ninja
export MESON_BUILD=1
cd /opt/flexran && ./flexran_build.sh -e -r 5gnr_sub6 -b
```

## Build container image with everything in

```
cd /opt
curl -L -O https://raw.githubusercontent.com/jianzzha/flexran/master/Dockerfile
mkdir -p auto
pushd /opt/auto && curl -L --remote-name-all https://raw.githubusercontent.com/jianzzha/flexran/master/auto/{setup.sh,cpu.py,threads.yaml,phycfg_timer.xml,testmac_cfg.xml} && popd
podman build -t flexran .
```

## Build container image with reduced size

```
cd /opt
curl -L -O https://raw.githubusercontent.com/jianzzha/flexran/master/Dockerfile.reduced
mkdir -p auto
pushd /opt/auto && curl -L --remote-name-all https://raw.githubusercontent.com/jianzzha/flexran/master/auto/{setup.sh,cpu.py,threads.yaml,phycfg_timer.xml,testmac_cfg.xml} && popd
podman build -t flexran -f Dockerfile.reduced .
```

## Verify flexran container image using podman

```podman run --name flexran -d --cap-add SYS_ADMIN --cap-add IPC_LOCK --cap-add SYS_NICE --mount 'type=bind,src=/sys,dst=/sys' --mount 'type=bind,src=/dev/hugepages,destination=/dev/hugepages' flexran:latest sleep infinity```

From terminal 1, run ```podman exec -it flexran sh```. The start directory is /opt/auto, run ```./setup.sh```. This will drop into the  PHY console.

Or instead of running the pod in deamon mode, one can directly drop into the PHY console in this way:
```podman run --name flexran -it --cap-add SYS_ADMIN --cap-add IPC_LOCK --cap-add SYS_NICE --mount 'type=bind,src=/sys,dst=/sys' --mount 'type=bind,src=/dev/hugepages,destination=/dev/hugepages' flexran:latest ./setup.sh```

From terminal 2, run ```podman exec -it flexran sh```. The start directory is /opt/auto, run ```./setup.sh l2```. This will drop into the TESTMAC console. From the console, do ```runall 0``` to kick off the test.

# Running Flexran from Openshift

## Install performance-addon operator

```
oc label --overwrite node worker1 node-role.kubernetes.io/worker-cnf=""
oc label --overwrite node worker1 feature.node.kubernetes.io/network-sriov.capable=true

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
  channel: "4.6"
  name: performance-addon-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF

while ! oc get pods -n openshift-performance-addon | grep Running; do
    echo "waiting for performance-addon operator online"
    sleep 5
done

cat <<EOF  | oc create -f -
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
while oc get sriovfecnodeconfigs | grep Succeeded; do
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
while oc get sriovfecnodeconfigs | grep Succeeded; do
    echo "waiting for sriovfecnodeconfigs succeeded"
    sleep 5
done

# make sure intel.com/intel_fec_acc100 show up
oc get node worker1 -o json | jq -r '.status.capacity' 
```

## Run flexran local test from Openshift with software FEC

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
    - mountPath: /lib/modules
      name: modules
    - mountPath: /dev
      name: dev
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
  - name: modules
    hostPath:
      path: /lib/modules
  - name: dev
    hostPath:
      path: /dev
  nodeSelector:
    node-role.kubernetes.io/worker-cnf: ""
EOF
```

After the pod is started, on terminal 1 run ```oc exec -it flextan sh```. This will start in /opt/auto directory. Kickoff the PHY by ```./setup.sh```.

on terminal 2 run ```oc exec -it flexran sh```. This will start in /opt/auto directory. Kick off the TESTMAC by ```./setup.sh l2```. From the TESTMAC console, execute ```runall 0``` to start the test.

To prevent the worker node from stalling during the test, two enviroment variables are supported. To raise the rcuc priority to 20 and ksoftirqd to 11, in the pod yaml env section, set rcuc=20 and ksoftirqd=11. Or one can manually set the ksoftirqd
on the worker node,
```
for p in `pgrep ksoftirqd`; do chrt -f --pid 11 $p; done
```

## Run flexran local test from Openshift with FEC hardware acceleration

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

After the pod is started, on terminal 1 run ```oc exec -it flextan sh```. This will start in /opt/auto directory. Kickoff the PHY by ```./setup.sh```.

on terminal 2 run ```oc exec -it flexran sh```. This will start in /opt/auto directory. Kick off the TESTMAC by ```./setup.sh l2```. From the TESTMAC console, execute ```runall 0``` to start the test.

To prevent the worker node from stalling during the test, two enviroment variables are supported. To raise the rcuc priority to 20 and ksoftirqd to 11, in the pod yaml env section, set rcuc=20 and ksoftirqd=11. Or one can manually set the ksoftirqd
on the worker node,
```
for p in `pgrep ksoftirqd`; do chrt -f --pid 11 $p; done
```

## Disable chronyd

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

## Enable ptp

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
  channel: "4.6"
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

## Create SRIOV VFs for front haul link

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
  channel: "4.6"
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

## Run front haul test from Openshift with FEC hardware acceleration

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
