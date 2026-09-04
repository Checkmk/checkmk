#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

HOOKROOT=/docker-entrypoint.d

exec_hook() {
    HOOKDIR="$HOOKROOT/$1"
    if [ -d "$HOOKDIR" ]; then
        pushd "$HOOKDIR" >/dev/null
        for hook in *; do
            if [ ! -d "$hook" ] && [ -x "$hook" ]; then
                echo "### Running $HOOKDIR/$hook"
                ./"$hook"
            fi
        done
        popd >/dev/null
    fi
}

create_system_apache_config() {
    # We have the special situation that the site apache is directly accessed from
    # external without a system apache reverse proxy. We need to disable the canonical
    # name redirect here to make redirects work as expected.
    #
    # In a reverse proxy setup the proxy would rewrite the host to the host requested by the user.
    # See omd/packages/apache-omd/skel/etc/apache/apache.conf for further information.
    #
    # The ServerName also needs to be in a special way. See
    # (https://forum.checkmk.com/t/check-mk-running-behind-lb-on-port-80-redirects-to-url-including-port-5000/16545)
    APACHE_DOCKER_CFG="/omd/sites/$CMK_SITE_ID/etc/apache/conf.d/cmk_docker.conf"
    echo -e "# Created for Checkmk docker container\\n\\nUseCanonicalName Off\\nServerName 127.0.0.1\\n" >"$APACHE_DOCKER_CFG"
    chown "$CMK_SITE_ID:$CMK_SITE_ID" "$APACHE_DOCKER_CFG"
    # Redirect top level requests to the sites base url
    echo -e "# Redirect top level requests to the sites base url\\nRedirectMatch 302 ^/$ /$CMK_SITE_ID/\\n" >>"$APACHE_DOCKER_CFG"
}

exec_hook pre-entrypoint

if [ -z "$CMK_SITE_ID" ]; then
    echo "ERROR: No site ID given"
    exit 1
fi

trap 'omd stop '"$CMK_SITE_ID"'; exit 0' SIGTERM SIGHUP SIGINT

# Prepare local MTA for sending to smart host
# TODO: Syslog is only added to support postfix. Can we please find a better solution?
if [ -n "$MAIL_RELAY_HOST" ]; then
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
    postconf -# myhostname

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

    create_system_apache_config

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
# volume was previously attached to a container with another Checkmk version.
# We now have to perform the "omd update" to be able to bring the site back
# to life.
if [ ! -e "/omd/sites/$CMK_SITE_ID/version" ]; then
    echo "### UPDATING SITE"
    exec_hook pre-update
    create_system_apache_config
    omd -f update --conflict=install "$CMK_SITE_ID"
    # Even if the system apache hook is not needed in containerized Checkmk, we
    # still create it for consistency
    omd update-apache-config "$CMK_SITE_ID"
    exec_hook post-update
fi

# Save the timezone configured at container level to the site environment
if [ -n "$TZ" ]; then
    if grep -E '^TZ=' "/opt/omd/sites/$CMK_SITE_ID/etc/environment" >/dev/null; then
        # Update an existing TZ setting
        sed -i -E "s#^TZ=.*#TZ=\"${TZ}\"#" "/opt/omd/sites/$CMK_SITE_ID/etc/environment"
    else
        # Write an inital timezone setting
        echo "TZ=\"${TZ}\"" >>"/opt/omd/sites/$CMK_SITE_ID/etc/environment"
    fi

    echo "Site timezone set to ${TZ}"
fi

# When a command is given via "docker run" use it instead of this script
if [ -n "$1" ]; then
    exec "$@"
fi

echo "### STARTING XINETD"
service xinetd start

echo "### STARTING SITE"
exec_hook pre-start
omd start "$CMK_SITE_ID"
exec_hook post-start

echo "### STARTING CRON"
cron -f &

echo "### CONTAINER STARTED"
wait
