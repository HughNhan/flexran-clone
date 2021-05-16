FROM quay.io/centos/centos
RUN yum install -y libhugetlbfs libhugetlbfs-devel libhugetlbfs-utils numactl-devel vim python3 pciutils iproute && pip3 install pyyaml
COPY flexran /opt/flexran
COPY dpdk /opt/dpdk
COPY intel /opt/intel
COPY auto /opt/auto
WORKDIR /opt/auto

