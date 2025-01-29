#!/usr/bin/env bash
set -e

echo "Tearing down OpenLDAP"
service slapd stop
apt remove -y slapd ldap-utils
apt purge -y slapd ldap-utils
apt autoremove -y
