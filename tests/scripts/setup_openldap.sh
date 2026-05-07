#!/usr/bin/env bash
set -e

if [ $# -ne 2 ]; then
    echo "Error: input arguments are missing. Please provide LDAP admin password and
path to the ldif file with content to add to LDAP.
Example cmdline: [sudo] ./setup_openldap.sh adminpassword ldap_content.ldif"
    exit 1
fi

LDAP_ADMIN_PASSWORD="$1"
CONTENT_FILE_PATH="$2"

echo "Setting up OpenLDAP"
debconf-set-selections <<<"slapd slapd/internal/generated_adminpw password ${LDAP_ADMIN_PASSWORD}"
debconf-set-selections <<<"slapd slapd/internal/adminpw password ${LDAP_ADMIN_PASSWORD}"
debconf-set-selections <<<"slapd slapd/password1 password ${LDAP_ADMIN_PASSWORD}"
debconf-set-selections <<<"slapd slapd/password2 password ${LDAP_ADMIN_PASSWORD}"
debconf-set-selections <<<"slapd slapd/domain string ldap.local"

DEBIAN_FRONTEND=noninteractive apt install -y slapd ldap-utils

# on k8s the env variable "POD_LABEL" is injected by Jenkins and might not be
# detected properly inside a pytest. The other env variable "KUBERNETES_PORT"
# is k8s native in every pod and independent of Jenkins env flags
if [ -f /.dockerenv ] || [ -n "$POD_LABEL" ] || [ -n "$KUBERNETES_PORT" ]; then
    echo "Dockerized or containerized environment detected (Docker or k8s)"
    service slapd start
    echo "service started, wait for a short period of time to fully come up"
    time timeout 10 bash -c 'until echo > /dev/tcp/localhost/389 2>/dev/null; do sleep 1; done'
    echo "Completed wait time, moving on"
else
    echo "No docker, no k8s detected"
fi

ldapadd -x -D cn=admin,dc=ldap,dc=local -w "${LDAP_ADMIN_PASSWORD}" -f "${CONTENT_FILE_PATH}"
