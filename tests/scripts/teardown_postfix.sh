#!/usr/bin/env bash
set -e

if [ -z "$1" ]; then
    echo "Error: A username is required as an argument.
This script will delete a Maildir for the provided username.
Example cmdline: [sudo] ./teardown_postfix.sh $(whoami)"
    exit 1
fi

echo "Stop postfix..."
if [ -f /.dockerenv ]; then
    postfix stop
else
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
