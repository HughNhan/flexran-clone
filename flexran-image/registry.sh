#/bin/sh

if [ "$EUID" -ne 0 ]
    then echo "Please run as root"
    exit 1
fi

set -euo pipefail

interface_name=$(ip route | sed -nr 's/^default.* dev ([[:alnum:]_-]+).*/\1/p' | head -1) 
ip_address=$(ip add show ${interface_name} | sed -nr 's/.*inet ([0-9.]+).*/\1/p')

### update /etc/pki/tls/openssl.cnf and update this section
sed -i '/^subjectAltName=/d' /etc/pki/tls/openssl.cnf
sed -i "/^\[ v3_ca \]/a subjectAltName=IP:${ip_address}" /etc/pki/tls/openssl.cnf
: <<'END'
The following is what will be in the /etc/pki/tls/openssl.cnf
[ v3_ca ]
subjectAltName=IP:${ip_address}
END

### create self cert
mkdir -p /opt/registry/{auth,certs,data}

host_fqdn=${ip_address}
cert_c="US"
cert_s="Massachussets"
cert_l="Boston"
cert_o="Red Hat, Inc"
cert_ou="Engineering"
cert_cn=${ip_address}

openssl req \
        -newkey rsa:4096 \
        -nodes \
        -sha256 \
        -keyout /opt/registry/certs/domain.key \
        -x509 \
        -days 365 \
        -out /opt/registry/certs/domain.crt \
        -subj "/C=${cert_c}/ST=${cert_s}/L=${cert_l}/O=${cert_o}/OU=${cert_ou}/CN=${cert_cn}"
        
### trus this self signed cert, so curl will not complain
/bin/cp -f /opt/registry/certs/domain.crt /etc/pki/ca-trust/source/anchors/
update-ca-trust enable
update-ca-trust extract

### let docker trust this self signed cert
mkdir -p /etc/containers/certs.d/${ip_address}:5000
/bin/cp -f /opt/registry/certs/domain.crt /etc/containers/certs.d/${ip_address}:5000/

### create http user: openshift , password: redhat
yum -y install  httpd httpd-tools podman
mkdir -p /opt/registry/auth/
htpasswd -bBc /opt/registry/auth/htpasswd openshift redhat

### create local volume for registry
mkdir -p /var/registry_vol

### start registry container
podman run -d  --privileged -p 5000:5000  --name registry \
       -e "REGISTRY_AUTH=htpasswd" -e "REGISTRY_AUTH_HTPASSWD_REALM=Registry Realm" \
       -e REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd \
       -v /var/registry_vol:/var/lib/registry -v /opt/registry/auth:/auth -v /opt/registry/certs:/certs \
       -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt \
       -e REGISTRY_HTTP_TLS_KEY=/certs/domain.key \
       docker.io/library/registry:2

### copy cert to http directory so that client can download it
if [[ -e /var/www/html ]]; then
    /bin/cp -f /opt/registry/certs/domain.crt /var/www/html
fi

### let's make systemd service for this pod so it restart on reboot
mkdir -p /usr/local/lib/systemd/system/
cat > /usr/local/lib/systemd/system/registry.service <<EOF
[Unit]
Description=private registry container
After=network-online.target
[Service]
Type=oneshot
RemainAfterExit=true
ExecStart=/usr/bin/podman start registry 
ExecStop=/usr/bin/podman stop -t 10 registry
[Install]
WantedBy=multi-user.target
EOF

systemctl enable registry.service
systemctl start registry.service
