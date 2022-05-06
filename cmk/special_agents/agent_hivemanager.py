#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import json
import sys

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

    auth = "%s:%s" % (user, password)
    auth_encoded = base64.encodebytes(auth.encode("utf-8")).decode("utf-8").replace("\n", "")
    headers = {
        "Authorization": "Basic %s" % auth_encoded,
        "Content-Type": "application/json",
    }
    try:
        data = requests.get("https://%s/hm/api/v1/devices" % ip, headers=headers).text
    except Exception as e:
        sys.stderr.write("Connection error: %s" % e)
        return 2

    informations = [
        "hostName",
        "clients",
        "alarm",
        "connection",
        "upTime",
        "eth0LLDPPort",
        "eth0LLDPSysName",
        "hive",
        "hiveOS",
        "hwmodel",
        "serialNumber",
        "nodeId",
        "location",
        "networkPolicy",
    ]

    print("<<<hivemanager_devices:sep(124)>>>")
    for line in json.loads(data):
        if line["upTime"] == "":
            line["upTime"] = "down"
        print("|".join(map(str, ["%s::%s" % (x, y) for x, y in line.items() if x in informations])))
    return None
