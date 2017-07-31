#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

"""Utility module for common code between the Event Console and other parts
of Check_MK. At the moment the GUI is accessing this module for gathering
the default configuration."""

import cmk.log

def default_config():
    return {
        "rules":          [], # old pre 1.2.7i1 format. Only used if rule_packs is empty
        "rule_packs":     [], # new format with rule packages
        "actions":        [],
        "debug_rules":    False,
        "rule_optimizer": True,
        "log_level":  {
            "cmk.mkeventd":              cmk.log.INFO,
            "cmk.mkeventd.EventServer":  cmk.log.INFO,
            "cmk.mkeventd.EventStatus":  cmk.log.INFO,
            "cmk.mkeventd.StatusServer": cmk.log.INFO,
        },
        "log_rulehits":          False,
        "log_messages":          False,
        "retention_interval":    60,
        "housekeeping_interval": 60,
        "statistics_interval":   5,
        "history_lifetime":      365 * 24 * 3600,
        "history_rotation":      "daily",
        "replication":           None,
        "remote_status":         None,
        "socket_queue_len":      10,
        "eventsocket_queue_len": 10,
        "hostname_translation":  {},
        "archive_orphans":       False,
        "archive_mode":          "file",
        "translate_snmptraps":   False,
        "snmp_credentials": [
            {
                "description": "\"public\" default for receiving SNMPv1/v2 traps",
                "credentials": "public",
            },
        ],
        "event_limit": {
            'by_host': {
                'action': 'stop_overflow_notify',
                'limit': 1000,
            },
            'by_rule': {
                'action': 'stop_overflow_notify',
                'limit': 1000,
            },
            'overall': {
                'action': 'stop_overflow_notify',
                'limit': 10000
            }
        },
    }


