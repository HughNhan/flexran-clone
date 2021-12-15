#/bin/sh
set -ex

manifest_url=https://github.com/redhat-partner-solutions/flexran-site-manifests
#get setup specific configuration
if [[ -e ~/flexran-site-manifests ]]; then
    /bin/rm -rf ~/flexran-site-manifests
fi
git clone ${manifest_url} ~/flexran-site-manifests
if [[ -e ~/flexran-site-manifests/setting.env ]]; then
    /bin/cp -f ~/flexran-site-manifests/setting.env ./setting.env
fi

export UPI_INSTALL="true"

./host_prep.sh & host_prep_pid=$!

wait $host_prep_pid


