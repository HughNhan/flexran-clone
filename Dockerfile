FROM quay.io/centos/centos
RUN yum install -y libhugetlbfs libhugetlbfs-devel libhugetlbfs-utils numactl-devel vim python3 pciutils iproute
WORKDIR /opt/
COPY flexran ./flexran
COPY dpdk ./dpdk
COPY intel ./intel
#COPY auto ./auto

