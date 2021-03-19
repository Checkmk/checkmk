#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import sys
from xml.etree import ElementTree as etree
from typing import Iterable, Optional, Sequence, Tuple
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


def pri_channels_section(
    *,
    credentials: Tuple[str, str, str, str],
    channels: Sequence[str],
) -> Iterable[str]:
    yield "<<<innovaphone_channels>>>"
    for channel_name, channel_data in _pri_channels_fetch_data(credentials, channels):
        yield _pri_channel_format_line(channel_name, channel_data)


def _pri_channels_fetch_data(
    credentials: Tuple[str, str, str, str],
    channels: Sequence[str],
) -> Iterable[Tuple[str, etree.Element]]:
    server, address, user, password = credentials
    for channel_name in channels:
        address = "http://%s/%s/mod_cmd.xml" % (server, channel_name)
        raw_data = get_url(address, user, password).read()
        if not raw_data:
            return
        yield channel_name, etree.parse(raw_data).getroot()


def _pri_channel_format_line(channel_name: str, data: etree.Element) -> str:
    link = data.get('link')
    physical = data.get('physical')
    if link != "Up" or physical != "Up":
        return "%s %s %s 0 0" % (channel_name, link, physical)
    idle = 0
    total = 0
    for channel in data.findall('ch'):
        if channel.get('state') == 'Idle':
            idle += 1
        total += 1
    total -= 1
    return "%s %s %s %s %s" % (channel_name, link, physical, idle, total)


def licenses_section(credentials) -> Iterable[str]:
    server, address, user, password = credentials
    address = "http://%s/PBX0/ADMIN/mod_cmd_login.xml" % server
    try:
        raw_data = get_url(address, user, password).read()
    except Exception:  # pylint: disable=broad-except # TODO: use requests 'raise_for_status'
        return

    yield "<<<innovaphone_licenses>>>"
    data = etree.parse(raw_data).getroot()
    for child in data.findall('lic'):
        if child.get('name') == "Port":
            count = child.get('count')
            used = child.get('used')
            yield f"{count} {used}"
            return


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

    sys.stdout.writelines(f"{line}\n" for line in pri_channels_section(
        credentials=credentials,
        channels=("PRI1", "PRI2", "PRI3", "PRI4"),
    ))

    sys.stdout.writelines(f"{line}\n" for line in licenses_section(credentials))


if __name__ == "__main__":
    sys.exit(main())
