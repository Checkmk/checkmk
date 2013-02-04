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
    mknotifyd_enabled = False

config_dir = defaults.default_config_dir + "/mknotifyd.d/wato/"

def log_mkeventd(what, message): 
    log_entry(None, what, message, "audit.log")     # central WATO audit log 
    log_entry(None, what, message, "mknotify.log")  # pending changes for mknotifyd

if mknotifyd_enabled:
    group = _("Notification")
    
    # Check_MK var
    register_configvar(group,
        "notification_spooling_enabled",
        Checkbox(
            title = _("Spool notifications"),
            help = _("Here you can set if notifications are processed through a spooling mechanism."
                     "Using notification spooling has the advantage that if there are problems on "
                     "sending a notification, the system tries to resend it later on. This is configurable "
                     "via the 'Notification fail retry interval'"),
            default_value = False),
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


    # Check_MK var
    register_configvar(group,
        "notification_forward_mode",
        DropdownChoice(
            title = _("Forwarding mode"),
            help = _("How notifications should be forwarded<br>"
                     "No Forwarding: Notifications are processed locally according to the contact settings<br>" 
                     "Forward an process local: Notifications are forwarded to the configured remote site, "
                     "but also processed locally according to the contacts settings<br>"
                     "Exclusive forwarding: Notifications are forwarded to the configured remote site and "
                     "never processed on the local site. This means that the configured notification plugins "
                     "for the local contacts do not apply"
                    ),
            choices = [
                ('off',       _("No Forwarding")),
                ('forward' ,  _("Forward and process local")),
                ('forward_exclusive', _("Exclusive forwarding"))
                ]),
        domain = "check_mk"
    )
    
    # Check_MK var
    register_configvar(group,
        "notification_forward_to",
        Optional(
            TextAscii(
                title = _("{Host}:{Port}")
            ),
            title = _("Forward notifications to remote host"),
            help = _("This will forward notifications to a remote site"),
            label = _("Forward to remote host"),
            none_label = _("Do not send to remote host"),
        ),
        domain = "check_mk"
    )
    
    # Daemon var
    register_configvar(group,
        "notification_daemon_listen_port",
            Integer(
                title = _("Port for receiving notifications"),
                help = _("Here you can set port at which the mknotifyd listens for forwarded"
                         "notification messages. The port number needs to be between 1025 and 65535"),
                minvalue = 1025,
                maxvalue = 65535,
                default_value = 6555,
            ),
        domain = "mknotifyd"
    )
    
