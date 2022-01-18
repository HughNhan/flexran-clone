#/bin/sh

set -euo pipefail

parse_args() {
   USAGE="Usage: $0 [options]
Options:
   [-s <Site specific manifest repo url>]  Download manifests from this repo

This script starts a end to end flexran setup and test.
"

    while getopts "s:h" opt
    do
        case ${opt} in
            s) manifest_url=$OPTARG ;;
            h) echo "$USAGE"; exit 0 ;;
            :) echo $USAGE; exit 1 ;;
            *) echo $USAGE; exit 1 ;;
        esac
    done
}

parse_args $@

if [[ -n ${manifest_url:-''} ]]; then
    if [[ -e ~/flexran-site-manifests ]]; then
        /bin/rm -rf ~/flexran-site-manifests
    fi
    git clone ${manifest_url} ~/flexran-site-manifests
    if [[ -e ~/flexran-site-manifests/setting.env ]]; then
        /bin/cp -f ~/flexran-site-manifests/setting.env ./setting.env
    fi
fi

exit 0
