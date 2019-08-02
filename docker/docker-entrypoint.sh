#!/bin/bash
set -e -o pipefail

HOOKROOT=/docker-entrypoint.d

function exec_hook() {
    HOOKDIR="$HOOKROOT/$1"
    if [ -d "$HOOKDIR" ]; then
        pushd "$HOOKDIR" >/dev/null
        for hook in *; do
            if [ ! -d "$hook" ] && [ -x "$hook" ]; then
                echo "### Running $HOOKDIR/$hook"
                ./"$hook" || true
            fi
        done
        popd >/dev/null
    fi
}

if [ -z "$CMK_SITE_ID" ]; then
    echo "ERROR: No site ID given"
    exit 1
fi

trap 'omd stop '"$CMK_SITE_ID"'; exit 0' SIGTERM SIGHUP SIGINT

# Prepare local MTA for sending to smart host
# TODO: Syslog is only added to support postfix. Can we please find a better solution?
if [ ! -z "$MAIL_RELAY_HOST" ]; then
    echo "### PREPARE POSTFIX (Hostname: $HOSTNAME, Relay host: $MAIL_RELAY_HOST)"
    echo "$HOSTNAME" >/etc/mailname
    postconf -e myorigin="$HOSTNAME"
    postconf -e mydestination="$(hostname -a), $(hostname -A), localhost.localdomain, localhost"
    postconf -e relayhost="$MAIL_RELAY_HOST"
    postconf -e mynetworks="127.0.0.0/8 [::ffff:127.0.0.0]/104 [::1]/128"
    postconf -e mailbox_size_limit=0
    postconf -e recipient_delimiter=+
    postconf -e inet_interfaces=all
    postconf -e inet_protocols=all

    echo "### STARTING MAIL SERVICES"
    syslogd
    /etc/init.d/postfix start
fi

# Create the site in case it does not exist
#
# Check for a file in the directory because the directory itself might have
# been pre-created by docker when the --tmpfs option is used to create a
# site tmpfs below tmp.
if [ ! -d "/opt/omd/sites/$CMK_SITE_ID/etc" ]; then
    echo "### CREATING SITE '$CMK_SITE_ID'"
    exec_hook pre-create
    omd create --no-tmpfs -u 1000 -g 1000 --admin-password "$CMK_PASSWORD" "$CMK_SITE_ID"
    omd config "$CMK_SITE_ID" set APACHE_TCP_ADDR 0.0.0.0
    omd config "$CMK_SITE_ID" set APACHE_TCP_PORT 5000

    if [ "$CMK_LIVESTATUS_TCP" = "on" ]; then
        omd config "$CMK_SITE_ID" set LIVESTATUS_TCP on
    fi
    exec_hook post-create
fi

# In case of an update (see update procedure docs) the container is started
# with the data volume mounted (the site is not re-created). In this
# situation only the site data directory is available and the "system level"
# parts are missing. Check for them here and create them.
## TODO: This should be supported by a omd command (omd init or similar)
if ! getent group "$CMK_SITE_ID" >/dev/null; then
    groupadd -g 1000 "$CMK_SITE_ID"
fi
if ! getent passwd "$CMK_SITE_ID" >/dev/null; then
    useradd -u 1000 -d "/omd/sites/$CMK_SITE_ID" -c "OMD site $CMK_SITE_ID" -g "$CMK_SITE_ID" -G omd -s /bin/bash "$CMK_SITE_ID"
fi
if [ ! -f "/omd/apache/$CMK_SITE_ID.conf" ]; then
    echo "Include /omd/sites/$CMK_SITE_ID/etc/apache/mode.conf" >"/omd/apache/$CMK_SITE_ID.conf"
fi

# In case the version symlink is dangling we are in an update situation: The
# volume was previously attached to a container with another Check_MK version.
# We now have to perform the "omd update" to be able to bring the site back
# to life.
if [ ! -e "/omd/sites/$CMK_SITE_ID/version" ]; then
    echo "### UPDATING SITE"
    exec_hook pre-update
    omd -f update --conflict=install "$CMK_SITE_ID"
    exec_hook post-update
fi

# When a command is given via "docker run" use it instead of this script
if [ -n "$1" ]; then
    exec "$@"
fi

echo "### STARTING SITE"
exec_hook pre-start
omd start "$CMK_SITE_ID"
exec_hook post-start

echo "### STARTING CRON"
cron -f &

echo "### CONTAINER STARTED"
wait
