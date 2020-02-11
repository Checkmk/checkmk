#!/usr/bin/env python
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
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from __future__ import print_function
import sys
import json
import base64
import requests


def main(sys_argv=None):
    if sys_argv is None:
        sys_argv = sys.argv[1:]

    try:
        ip = sys_argv[0]
        user = sys_argv[1]
        password = sys_argv[2]
    except IndexError:
        sys.stderr.write("Usage: agent_hivemanager <IP> <USERNAME> <PASSWORD>\n")
        return 2

    base64string = base64.encodestring('%s:%s' % (user, password)).replace('\n', '')
    headers = {"Authorization": "Basic %s" % base64string, "Content-Type": "application/json"}
    try:
        data = requests.get("https://%s/hm/api/v1/devices" % ip, headers=headers).text
    except Exception as e:
        sys.stderr.write("Connection error: %s" % e)
        return 2

    informations = [
        'hostName',
        'clients',
        'alarm',
        'connection',
        'upTime',
        'eth0LLDPPort',
        'eth0LLDPSysName',
        'hive',
        'hiveOS',
        'hwmodel'
        'serialNumber',
        'nodeId',
        'location',
        'networkPolicy',
    ]

    print("<<<hivemanager_devices:sep(124)>>>")
    for line in json.loads(data):
        if line['upTime'] == '':
            line['upTime'] = "down"
        print("|".join(map(str, ["%s::%s" % (x, y) for x, y in line.items() if x in informations])))
