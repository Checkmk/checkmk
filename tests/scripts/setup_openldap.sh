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

if [ -f /.dockerenv ]; then
    service slapd start
fi

ldapadd -x -D cn=admin,dc=ldap,dc=local -w "${LDAP_ADMIN_PASSWORD}" -f "${CONTENT_FILE_PATH}"
