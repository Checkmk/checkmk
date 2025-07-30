#!/usr/bin/env bash
# Create CA key and certificate
# Output folder
_SRVDIR=~/postgres/ssl_server_files
_CLIDIR=~/postgres/ssl_client_files
# Validity
_DAYSVALID=3650

if [ ! -f "/etc/postgresql/ssl/root.key" ]; then
    openssl genrsa -out "${_SRVDIR}/root.key" 4096
    openssl req -x509 -new -nodes -key "${_SRVDIR}/root.key" -sha256 -days "${_DAYSVALID}" -out "${_SRVDIR}/root.crt" -subj "/CN=QA Root CA"
    openssl genrsa -out "${_SRVDIR}/server.key" 4096
    openssl req -new -key "${_SRVDIR}/server.key" -out "${_SRVDIR}/server.csr" -subj "/CN=$(hostname --fqdn)"
    openssl x509 -req -in "${_SRVDIR}/server.csr" -CA "${_SRVDIR}/root.crt" -CAkey "${_SRVDIR}/root.key" -CAcreateserial -out "${_SRVDIR}/server.crt" -days "${_DAYSVALID}" -sha256

    mkdir /etc/postgresql/ssl
    cp "${_SRVDIR}"/* /etc/postgresql/ssl
    chown -R postgres:postgres /etc/postgresql/ssl
    systemctl restart postgresql
    systemctl status postgresql
else
    echo "Setup already done! To rerun, remove or rename /etc/postgresql/ssl."
fi
