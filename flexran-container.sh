FLEXRAN_DIR=${FLEXRAN_DIR:-/root/flexran}
DPDK_DIR=${DPDK_DIR:-/root/flexran/dpdk}
STAGING_DIR=${STAGING_DIR:-/root/staging}
ICC_DIR=${ICC_DIR:-/opt/intel/system_studio_2019}


echo "setting up staging area"
/bin/rm -rf $STAGING_DIR 2>/dev/null
mkdir -p $STAGING_DIR/flexran/{xran,sdk,dpdk,icc,tests,auto}
/bin/cp -r $FLEXRAN_DIR/{wls_mod,libs,misc,bin} $STAGING_DIR/flexran/
/bin/cp -r $FLEXRAN_DIR/xran/{app,banner.txt,build.sh,lib,Licenses.txt,misc,readme.md,test} $STAGING_DIR/flexran/xran/
/bin/cp -r $FLEXRAN_DIR/sdk/build-avx512-icc $STAGING_DIR/flexran/sdk/
/bin/cp -r $DPDK_DIR/{app,devtools,drivers,kernel,lib,license,usertools} $STAGING_DIR/flexran/dpdk/
/bin/cp -r auto/* $STAGING_DIR/flexran/auto/
/bin/cp -r $ICC_DIR/compilers_and_libraries_2019.5.281/linux/compiler/lib/intel64_lin/* $ICC_DIR/compilers_and_libraries_2019/linux/mkl/lib/intel64_lin/* $ICC_DIR/compilers_and_libraries_2019/linux/ipp/lib/intel64_lin/* $STAGING_DIR/flexran/icc/
/bin/cp -r $FLEXRAN_DIR/tests/nr5g $STAGING_DIR/flexran/tests/

cat >$STAGING_DIR/flexran/auto/env.src <<EOF
export RTE_SDK=/opt/flexran/dpdk
export RTE_TARGET=x86_64-native-linuxapp-icc 
export DIR_WIRELESS_SDK_ROOT=/opt/flexran/sdk
export WIRELESS_SDK_TARGET_ISA=avx512
export SDK_BUILD=build-avx512-icc
export DIR_WIRELESS_SDK=/opt/flexran/sdk/build-avx512-icc
export MLOG_DIR=/opt/flexran/libs/mlog
export XRAN_DIR=/opt/flexran/xran
export ROE_DIR=/opt/flexran/libs/roe
export RPE_DIR=/opt/flexran/libs/ferrybridge
export DIR_WIRELESS_TEST_5G=/opt/flexran/tests/nr5g      
export DIR_WIRELESS_TABLE_5G=/opt/flexran/bin/nr5g/gnb/l1/table
export FLEXRAN_SDK=/opt/flexran/sdk/build-avx512-icc/install
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/flexran/icc
EOF

echo "writing Dockerfile"
cat >$STAGING_DIR/Dockerfile <<EOF
FROM quay.io/centos/centos 
RUN yum install -y libhugetlbfs libhugetlbfs-devel libhugetlbfs-utils numactl-devel vim python3 pciutils iproute && pip3 install pyyaml
COPY flexran /opt/flexran
WORKDIR /opt/flexran
EOF

echo "building image"
pushd $STAGING_DIR/
podman build -t flexran .
