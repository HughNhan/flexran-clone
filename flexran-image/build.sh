#!/bin/sh

FLEXRAN_DIR=${FLEXRAN_DIR:-/opt/flexran}
DPDK_DIR=${DPDK_DIR:-/opt/dpdk}
STAGING_DIR=${STAGING_DIR:-${HOME}/staging}
ICC_DIR=${ICC_DIR:-/opt/intel/system_studio_2019}
IMAGE_REPO=${IMAGE_REPO:-10.16.231.128:5000}
FLEXRAN_VERSION=$(basename ${FLEXRAN_DIR}/SDK*.sh | sed -n -r 's/SDK-([0-9.]+)\.sh/\1/p')

set -eu

print_usage() {
    declare -A arr
    arr+=( ["build"]="Build flexran container image"
           ["push"]="Push flexran container image to repo"
           ["purge"]="Purge dangling container images"
           ["clean"]="Cleanup staging directory and delete flexran container image"
         )
    echo "Usage:"
    echo ""
    for key in ${!arr[@]}; do
        printf '%-15s: %s\n' "$key" "${arr[$key]}"
    done
    exit 1
}

purge() {
    echo "purge old images ..."
    podman rmi -f $(podman images -f dangling=true -q) 2>/dev/null || true
    exit 0
}

clean() {
    echo "cleanup existing container image and staging directory"
    podman rmi ${IMAGE_REPO}/flexran:${FLEXRAN_VERSION} 2>/dev/null || true
    /bin/rm -rf ${STAGING_DIR}
}

build() {
    #  only update staging if the right version is not present
    if [ ! -e ${STAGING_DIR}/${FLEXRAN_VERSION} ]; then
        echo "update staging area"
        /bin/rm -rf $STAGING_DIR 2>/dev/null
        mkdir -p $STAGING_DIR/flexran/{xran,sdk,dpdk,icc,tests,auto}
        /bin/cp -r $FLEXRAN_DIR/{wls_mod,libs,misc,bin} $STAGING_DIR/flexran/
        /bin/cp -r $FLEXRAN_DIR/xran/{app,banner.txt,build.sh,lib,Licenses.txt,misc,readme.md,test} $STAGING_DIR/flexran/xran/
        /bin/cp -r $FLEXRAN_DIR/sdk/build-avx512-icc $STAGING_DIR/flexran/sdk/
        /bin/cp -r $DPDK_DIR/{app,devtools,drivers,kernel,lib,license,usertools} $STAGING_DIR/flexran/dpdk/
        /bin/cp -r $ICC_DIR/compilers_and_libraries_2019.5.281/linux/compiler/lib/intel64_lin/* $ICC_DIR/compilers_and_libraries_2019/linux/mkl/lib/intel64_lin/* $ICC_DIR/compilers_and_libraries_2019/linux/ipp/lib/intel64_lin/* $STAGING_DIR/flexran/icc/
        /bin/cp -r $FLEXRAN_DIR/tests/nr5g $STAGING_DIR/flexran/tests/
        /bin/cp ./{env.src,driver.sh} $STAGING_DIR/flexran/auto/
        /bin/cp -f Dockerfile ${STAGING_DIR}/
        touch ${STAGING_DIR}/${FLEXRAN_VERSION}
    else
        echo "staging area is up to date"
    fi
    
    rebuild="false"
    if podman inspect ${IMAGE_REPO}/flexran:${FLEXRAN_VERSION} >/dev/null 2>&1; then
        timestamp_image=$(podman inspect -f '{{ .Created }}' ${IMAGE_REPO}/flexran:${FLEXRAN_VERSION} | awk '{--NF;print $0}')
        epoch_image=$(date --date="${timestamp_image}" +"%s")
        for f in Dockerfile driver.sh env.src; do
            epoch_file=$(ls --time-style=+%s -l $f | awk "{print(\$6)}")
            # if image is newer than dockerfile, no need to rebuild 
            if ((epoch_file > epoch_image)); then
                /bin/cp -f $f ${STAGING_DIR}/
                rebuild="true"
            fi
        done
    else
        rebuild="true"
    fi    
    
    if [[ "${rebuild}" == "true" ]]; then
        echo "building image"
        pushd $STAGING_DIR/
        podman build -t ${IMAGE_REPO}/flexran:${FLEXRAN_VERSION} .
        popd
    else
        echo "docker image is up to date"
    fi
}


push() {
    build
    echo "pushing container image to repo ${IMAGE_REPO}"
    podman push ${IMAGE_REPO}/flexran:${FLEXRAN_VERSION}
}


if (( $# != 1 )); then
    print_usage 
else
    ACTION=$1
fi

case "${ACTION}" in
    build)
        build 
    ;;
    push)
        push 
    ;;
    clean)
        clean
    ;;
    purge)
        purge
    ;;
    *)
        print_usage 
esac


