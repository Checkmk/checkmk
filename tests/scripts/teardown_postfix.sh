#!/usr/bin/env bash
set -e

if [ -z "$1" ]; then
    echo "Error: A username is required as an argument.
This script will delete a Maildir for the provided username.
Example cmdline: [sudo] ./teardown_postfix.sh $(whoami)"
    exit 1
fi

echo "Stop postfix..."
# on k8s the env variable "POD_LABEL" is injected by Jenkins and might not be
# detected properly inside a pytest. The other env variable "KUBERNETES_PORT"
# is k8s native in every pod and independent of Jenkins env flags
if [ -f /.dockerenv ] || [ -n "$POD_LABEL" ] || [ -n "$KUBERNETES_PORT" ]; then
    echo "Dockerized or containerized environment detected (Docker or k8s)"
    service postfix stop
    echo "postfix stopped"
else
    echo "No docker, no k8s detected"
    systemctl stop postfix
fi

echo "Remove postfix..."
apt-get remove -y postfix
apt-get purge postfix -y
rm -rf /etc/postfix/
rm -rf /var/lib/postfix
rm -rf /var/spool/postfix

echo "Remove maildir..."
home_directory=$(eval echo ~"$1")
rm -rf "${home_directory}/Maildir"
