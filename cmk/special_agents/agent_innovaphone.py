#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import xml.etree.ElementTree as etree

from six import ensure_binary, ensure_str


def get_informations(credentials, name, xml_id, org_name):
    server, address, user, password = credentials
    data_url = "/LOG0/CNT/mod_cmd.xml?cmd=xml-count&x="
    address = "http://%s%s%s" % (server, data_url, xml_id)
    data = _get_element(get_url(address, user, password))
    if data is None:
        return

    c = None
    for line in data:
        for child in line:
            if child.get('c'):
                c = child.get('c')
    if c:
        print("<<<%s>>>" % name)
        print(org_name + " " + c)


def get_pri_channel(credentials, channel_name):
    server, address, user, password = credentials
    data_url = "/%s/mod_cmd.xml" % channel_name
    address = "http://%s%s" % (server, data_url)
    data = _get_element(get_url(address, user, password))
    if data is None:  # no such channel
        return

    link = data.get('link')
    physical = data.get('physical')
    if link != "Up" or physical != "Up":
        print("%s %s %s 0 0 0" % (channel_name, link, physical))
        return
    idle = 0
    total = 0
    for channel in data.findall('ch'):
        if channel.get('state') == 'Idle':
            idle += 1
        total += 1
    total -= 1
    print("%s %s %s %s %s" % (channel_name, link, physical, idle, total))


def get_licenses(credentials):
    server, address, user, password = credentials
    address = "http://%s/PBX0/ADMIN/mod_cmd_login.xml" % server
    try:
        data = _get_element(get_url(address, user, password))
    except HTTPError as exc:
        if exc.reason == "Unauthorized":
            return
        raise

    if data is None:
        return

    print("<<<innovaphone_licenses>>>")
    for child in data.findall('lic'):
        if child.get('name') == "Port":
            count = child.get('count')
            used = child.get('used')
            print(count, used)
            break


def get_url(address, user, password):
    request = Request(address)
    base64string = base64.encodebytes(ensure_binary('%s:%s' % (user, password))).replace(b'\n', b'')
    request.add_header("Authorization", "Basic %s" % ensure_str(base64string))
    return urlopen(request)


def _get_element(stream):
    try:
        return etree.parse(stream).getroot()
    except etree.ParseError as err:
        sys.stderr.write("ERROR: %s\n" % err)
    return None


def main(sys_argv=None):
    if sys_argv is None:
        sys_argv = sys.argv[1:]

    if len(sys_argv) != 3:
        sys.stderr.write("usage: agent_innovaphone HOST USER PASSWORD\n")
        return 1

    server = sys_argv[0]
    user = sys_argv[1]
    password = sys_argv[2]

    base_url = "/LOG0/CNT/mod_cmd.xml?cmd=xml-counts"
    counter_address = "http://%s%s" % (server, base_url)

    credentials = (server, counter_address, user, password)

    p = etree.parse(get_url(counter_address, user, password))
    root_data = p.getroot()

    informations = {}
    for entry in root_data:
        n = entry.get('n')
        x = entry.get('x')
        informations[n] = x

    s_prefix = "innovaphone_"
    for what in ["CPU", "MEM", "TEMP"]:
        if informations.get(what):
            section_name = s_prefix + what.lower()
            get_informations(credentials, section_name, informations[what], what)

    print("<<<%schannels>>>" % s_prefix)
    for channel_num in range(1, 5):
        get_pri_channel(credentials, 'PRI' + str(channel_num))

    get_licenses(credentials)
