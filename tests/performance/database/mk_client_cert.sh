#!/usr/bin/env bash
# Create client key and certificate
# Output folder
_SRVDIR=~/postgres/ssl_server_files
_CLIDIR=~/postgres/ssl_client_files
# Validity
_DAYSVALID=3650
read -r -e -p "CN? " -i "performance" _CN
mkdir -p "${_CLIDIR}/${_CN}"
openssl genrsa -out "${_CLIDIR}/${_CN}/postgresql.key" 4096
openssl req -new -key "${_CLIDIR}/${_CN}/postgresql.key" -out "${_CLIDIR}/${_CN}/postgresql.csr" -subj "/CN=${_CN}"
openssl x509 -req -in "${_CLIDIR}/${_CN}/postgresql.csr" -CA "${_SRVDIR}/root.crt" -CAkey "${_SRVDIR}/root.key" -CAcreateserial -out "${_CLIDIR}/${_CN}/postgresql.crt" -days "${_DAYSVALID}" -sha256
