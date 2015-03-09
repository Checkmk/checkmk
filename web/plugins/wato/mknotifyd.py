#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

mknotifyd_config_dir = defaults.default_config_dir + "/mknotifyd.d/wato/"

if mknotifyd_enabled:
    replication_paths.append(( "dir",  "mknotify",  mknotifyd_config_dir))
    backup_paths.append(( "dir",  "mknotify",  mknotifyd_config_dir))

    group = _("Notification")

    # Check_MK var
    register_configvar(group,
        "notification_spooling",
        Transform(
            DropdownChoice(
                title = _("Notification Spooling"),
                choices = [
                    ( "off",    _("Direct local delivery without spooling") ),
                    ( "local",  _("Asynchronous local delivery by notification spooler") ),
                    ( "remote", _("Forward to remote site by notification spooler") ),
                    ( "both",   _("Asynchronous local delivery plus remote forwarding" ) ),
                ],
                default_value = False,
                help = _("This option dedices how notifications will be processed. Without the "
                         "notification spooler (<tt>mknotifyd</tt>) only direct local delivery "
                         "is possible. Long lasting or excessive notifications might slow down "
                         "the monitoring. If you select remote forwarding then make sure that "
                         "your notification spooler is correctly setup for incoming and/or "
                         "outgoing connections."),
            ),
            forth = lambda x: (x == False and "off" or (x == True and "local" or x)),
        ),
        domain = "check_mk",
    )


    # Daemon var
    register_configvar_domain("mknotifyd", mknotifyd_config_dir)
    register_configvar(group,
        "config",
        Dictionary(
            title = _("Notification Spooler Configuration"),
            elements = [
                ( "log_level",
                  DropdownChoice(
                      title = _("Verbosity of logging"),
                      choices = [
                        ( 0, _("Normal logging (only startup, shutdown and errors)") ),
                        ( 1, _("Verbose logging (also spooled notifications)") ),
                        ( 2, _("Debugging (log every single action)") ),
                      ],
                      default_value = 0,
                )),
                ( "deferred_cooldown",
                  Age(
                      title = _("Cooldown time before retrying delivery"),
                      minvalue = 1,
                      maxvalue = 86400,
                      default_value = 180,
                )),
                ( "incoming",
                  Dictionary(
                      columns = 2,
                      title = _("Accept incoming TCP connections"),
                      elements = [
                          ( "listen_port",
                            Integer(
                                title = _("TCP Port"),
                                minvalue = 1024,
                                maxvalue = 65535,
                                default_value = 6555,
                          )),
                          ( "heartbeat_interval",
                            Age(
                                title = _("Interval at which to <b>send</b> regular heart beats"),
                                minvalue = 1,
                                default_value = 10,
                          )),
                      ],
                      optional_keys = None,
                )),
                ( "outgoing",
                  ListOf(
                      Dictionary(
                          columns = 2,
                          elements = [
                              ( "address",
                                Hostname(
                                    title = _("DNS name or IP address of target notification spooler"),
                              )),
                              ( "port",
                                Integer(
                                    title = _("TCP Port"),
                                    minvalue = 1,
                                    maxvalue = 65535,
                                    default_value = 6555,
                              )),
                              ( "cooldown",
                                Age(
                                    title = _("Cooldown time before trying to reconnect after failure"),
                                    minvalue = 1,
                                    default_value = 20,
                              )),
                              ( "heartbeat_interval",
                                Age(
                                    title = _("Interval at which to <b>expect</b> regular beats"),
                                    minvalue = 1,
                                    default_value = 10,
                              )),
                              ( "heartbeat_timeout",
                                Age(
                                    title = _("Maximum expected run time for heart beat packet"),
                                    minvalue = 1,
                                    default_value = 3,
                              )),
                          ],
                          optional_keys = None,
                      ),
                      title = _("Connect to remote sites"),
                      add_label = _("Add connection"),
                )),

            ],
            optional_keys = [ "incoming", ],
        ),
        domain = "mknotifyd",
    )


    ### register_configvar(group,
    ###     "notification_deferred_retention_time",
    ###         Integer(
    ###             title = _("Notification fail retry interval"),
    ###             help = _("If the processing of a notification fails, the notify daemon "
    ###                      "retries to send the notification again after this time"),
    ###             minvalue = 10,
    ###             maxvalue = 86400,
    ###             default_value = 180,
    ###             unit = _("Seconds")
    ###         ),
    ###     domain = "mknotifyd"
    ### )


    ### # Daemon var
    ### register_configvar(group,
    ###     "notification_daemon_listen_port",
    ###     Optional(
    ###         Integer(
    ###             minvalue = 1024,
    ###             maxvalue = 65535,
    ###             default_value = 6555,
    ###         ),
    ###         help = _("Here you can set the port at which the notification spooler listens for forwarded"
    ###                  "notification messages from spoolers on remote sites."),
    ###         title = _("Port for receiving notifications"),
    ###         label = _("Receive notifications from remote sites"),
    ###         none_label = _("(Do not receive notifications)"),
    ###     ),
    ###     domain = "mknotifyd"
    ### )

