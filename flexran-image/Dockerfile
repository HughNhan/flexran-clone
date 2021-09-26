FROM registry.access.redhat.com/ubi8:latest
RUN dnf install -y rsync kmod libhugetlbfs libhugetlbfs-devel libhugetlbfs-utils \
        numactl-devel vim python3 pciutils iproute \
     && dnf clean all \
     && rm -rf /var/cache/yum \
     && pip3 install pyyaml
COPY flexran /opt/flexran
WORKDIR /opt/flexran/auto

