#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import sys
import xml.etree.ElementTree as etree
from typing import Optional, Sequence
from urllib.request import Request, urlopen

from six import ensure_binary, ensure_str

from cmk.special_agents.utils.argument_parsing import (
    Args,
    create_default_argument_parser,
)


def get_informations(credentials, name, xml_id, org_name):
    server, address, user, password = credentials
    data_url = "/LOG0/CNT/mod_cmd.xml?cmd=xml-count&x="
    address = "http://%s%s%s" % (server, data_url, xml_id)
    c = None
    for line in etree.parse(get_url(address, user, password)).getroot():
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
    data = etree.parse(get_url(address, user, password)).getroot()
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
    data = etree.parse(get_url(address, user, password)).getroot()
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


def parse_arguments(argv: Optional[Sequence[str]]) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument("user", metavar="USER")
    parser.add_argument("password", metavar="PASSWORD")
    parser.add_argument("host", metavar="HOST")
    return parser.parse_args(argv)


def main(sys_argv=None):
    if sys_argv is None:
        sys_argv = sys.argv[1:]
    args = parse_arguments(sys_argv)

    counter_address = f"http://{args.host}/LOG0/CNT/mod_cmd.xml?cmd=xml-counts"
    credentials = (args.host, counter_address, args.user, args.password)
    p = etree.parse(get_url(counter_address, args.user, args.password))
    root_data = p.getroot()

    informations = {}
    for entry in root_data:
        n = entry.get('n')
        x = entry.get('x')
        informations[n] = x

    for what in ["CPU", "MEM", "TEMP"]:
        if informations.get(what):
            section_name = "innovaphone_" + what.lower()
            get_informations(credentials, section_name, informations[what], what)

    print("<<<innovaphone_channels>>>")
    for channel_num in range(1, 5):
        get_pri_channel(credentials, 'PRI' + str(channel_num))

    print("<<<innovaphone_licenses>>>")
    get_licenses(credentials)


if __name__ == "__main__":
    sys.exit(main())
