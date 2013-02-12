#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import config 

try:
    mknotifyd_enabled = config.mknotifyd_enabled
except:
    # Non OMD-users: must enable this explicitely, sorry
    mknotifyd_enabled = False

config_dir = defaults.default_config_dir + "/mknotifyd.d/wato/"

if mknotifyd_enabled:
    group = _("Notification")
    
    # Check_MK var
    register_configvar(group,
        "notification_spooling",
        Checkbox(
            title = _("Spool notifications"),
            help = _("Here you can set if notifications are processed through a spooling mechanism."
                     "Using notification spooling has the advantage that if there are problems on "
                     "sending a notification, the system tries to resend it later on. This is configurable "
                     "via the 'Notification fail retry interval'"),
            default_value = False),
        domain = "check_mk"
    )
    
    # Check_MK var
    register_configvar(group,
        "notification_spool_to",
        Optional(
            Tuple(
                elements = [
                    TextAscii(
                        title = _("Remote host"),
                    ),
                    Integer(
                        title = _("TCP port"),
                        minvalue = 1,
                        maxvalue = 65535,
                        default_value = 6555,
                    ),
                    Checkbox(
                        title = _("Local processing"),
                        label = _("Also process notification locally"),
                    ),
                ]),
            title = _("Remote notification spooling"),
            help = _("This option allows you to forward notifications to another Check_MK site. "
                     "That site must have the notification spooler running and TCP listening enabled. "
                     "This allows you to create a centralized notification handling."),
            label = _("Spool notifications to remote site"),
            none_label = _("(Do not spool to remote site)"),
        ),
        domain = "check_mk"
    )
    
    # Daemon var
    register_configvar_domain("mknotifyd", config_dir)
    register_configvar(group,
        "notification_deferred_retention_time",
            Integer(
                title = _("Notification fail retry interval"),
                help = _("If the processing of a notification fails, the notify daemon "
                         "retries to send the notification again after this time"),
                minvalue = 10,
                maxvalue = 86400,
                default_value = 180,
                unit = _("Seconds")
            ),
        domain = "mknotifyd"
    )


    # Daemon var
    register_configvar(group,
        "notification_daemon_listen_port",
        Optional(
            Integer(
                minvalue = 1,
                maxvalue = 65535,
                default_value = 6555,
            ),
            help = _("Here you can set the port at which the notification spooler listens for forwarded"
                     "notification messages from spoolers on remote sites."),
            title = _("Port for receiving notifications"),
            label = _("Receive notifications from remote sites"),
            none_label = _("(Do not receive notifications)"),
        ),
        domain = "mknotifyd"
    )
    
