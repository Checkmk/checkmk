#!/usr/bin/env bash
set -e

if [ -z "$1" ]; then
    echo "Error: A username is required as an argument.
This script will create a Maildir for the provided username
and configure Postfix to deliver emails to this Maildir.
Example cmdline: [sudo] ./setup_postfix.sh $(whoami)"
    exit 1
fi

echo "Installing postfix..."
debconf-set-selections <<<"postfix postfix/mailname string test.email.com"
debconf-set-selections <<<"postfix postfix/main_mailer_type string 'Internet Site'"

DEBIAN_FRONTEND=noninteractive apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y postfix

echo "Redirect email to current user..."
username=$1
echo "@test.com $username" >>/etc/postfix/virtual

echo "Update postfix configuration..."
echo -e "home_mailbox = Maildir/
virtual_transport = local
virtual_alias_maps = hash:/etc/postfix/virtual" >>/etc/postfix/main.cf

echo "Update virtual alias map..."
postmap /etc/postfix/virtual

echo "Start postfix..."
# on k8s the env variable "POD_LABEL" is injected by Jenkins and might not be
# detected properly inside a pytest. The other env variable "KUBERNETES_PORT"
# is k8s native in every pod and independent of Jenkins env flags
if [ -f /.dockerenv ] || [ -n "$POD_LABEL" ] || [ -n "$KUBERNETES_PORT" ]; then
    echo "Dockerized or containerized environment detected (Docker or k8s)"
    service postfix start
    echo "postfix started, wait for a short period of time to fully come up"
    sleep 5
    echo "Completed wait time, moving on"
else
    echo "No docker, no k8s detected"
    systemctl start postfix
fi
