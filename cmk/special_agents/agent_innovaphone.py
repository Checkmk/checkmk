#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
import urllib.parse
from typing import Iterable, Optional, Sequence, Tuple
from xml.etree import ElementTree as etree

import requests

import cmk.utils.password_store

from cmk.special_agents.utils.argument_parsing import Args, create_default_argument_parser


class InnovaphoneConnection:
    def __init__(self, *, host, protocol, user, password, verify_ssl) -> None:
        self._base_url = f"{protocol}://{host}"
        self._user = user
        self._password = password
        self._session = requests.Session()
        # we cannot use self._session.verify because it will be overwritten by
        # the REQUESTS_CA_BUNDLE env variable
        self._verify_ssl = verify_ssl

    def get(self, endpoint):
        try:
            # we must provide the verify keyword to every individual request call!
            url = urllib.parse.urljoin(self._base_url, endpoint)
            response = self._session.get(
                url,
                verify=self._verify_ssl,
                auth=(self._user, self._password),
            )
        except requests.exceptions.RequestException as e:
            sys.stderr.write(f"ERROR while connecting to {url}: {e}\n")
            return None

        if response.status_code != 200:
            sys.stderr.write(
                f"ERROR while processing request [{response.status_code}]: {response.reason}\n"
            )
        return response.text


def get_informations(connection: InnovaphoneConnection, name, xml_id, org_name):
    url = "LOG0/CNT/mod_cmd.xml?cmd=xml-count&x=%s" % (xml_id)
    response = connection.get(url)
    if response is None:
        return
    data = _get_element(response)
    if data is None:
        return

    c = None
    for line in data:
        for child in line:
            if child.get("c"):
                c = child.get("c")
    if c:
        print("<<<%s>>>" % name)
        print(org_name + " " + c)


def pri_channels_section(
    *,
    connection: InnovaphoneConnection,
    channels: Sequence[str],
) -> Iterable[str]:
    yield "<<<innovaphone_channels>>>"
    for channel_name, channel_data in _pri_channels_fetch_data(connection, channels):
        yield _pri_channel_format_line(channel_name, channel_data)


def _pri_channels_fetch_data(
    connection: InnovaphoneConnection,
    channels: Sequence[str],
) -> Iterable[Tuple[str, etree.Element]]:
    for channel_name in channels:
        url = "%s/mod_cmd.xml" % channel_name
        response = connection.get(url)
        if response is None:
            return
        if response == "?\r\n":
            # ignore response for invalid module names. For details see
            # https://wiki.innovaphone.com/index.php?title=Howto:Effect_arbitrary_Configuration_Changes_using_a_HTTP_Command_Line_Client_or_from_an_Update
            return
        data = _get_element(response)
        if data is None:
            return
        yield channel_name, data


def _pri_channel_format_line(channel_name: str, data: etree.Element) -> str:
    link = data.get("link")
    physical = data.get("physical")
    if link != "Up" or physical != "Up":
        return "%s %s %s 0 0" % (channel_name, link, physical)
    idle = 0
    total = 0
    for channel in data.findall("ch"):
        if channel.get("state") == "Idle":
            idle += 1
        total += 1
    total -= 1
    return "%s %s %s %s %s" % (channel_name, link, physical, idle, total)


def licenses_section(connection: InnovaphoneConnection) -> Iterable[str]:
    url = "PBX0/ADMIN/mod_cmd_login.xml"
    response = connection.get(url)
    if response is None:
        return
    data = _get_element(response)

    if data is None:
        return

    yield "<<<innovaphone_licenses>>>"
    for child in data.findall("lic"):
        if child.get("name") == "Port":
            count = child.get("count")
            used = child.get("used")
            yield f"{count} {used}"
            return


def _get_element(text: str) -> Optional[etree.Element]:
    try:
        return etree.fromstring(text)
    except etree.ParseError as e:
        # this is a bit broad. But for now it fixes the agent.
        sys.stderr.write(f"ERROR while parsing: {e}\n")
    return None


def parse_arguments(argv: Optional[Sequence[str]]) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument("host", metavar="HOST")
    parser.add_argument("user", metavar="USER")
    parser.add_argument("password", metavar="PASSWORD")
    parser.add_argument(
        "--protocol",
        choices=[
            "http",
            "https",
        ],
        default="https",
        help="specify the connection protocol (default: https)",
    )
    parser.add_argument(
        "--no-cert-check",
        action="store_true",
        help="Disable certificate verification",
    )
    return parser.parse_args(argv)


def main(sys_argv=None):
    if sys_argv is None:
        cmk.utils.password_store.replace_passwords()
        sys_argv = sys.argv[1:]
    args = parse_arguments(sys_argv)
    connection = InnovaphoneConnection(
        host=args.host,
        protocol=args.protocol,
        user=args.user,
        password=args.password,
        verify_ssl=not args.no_cert_check,
    )

    response = connection.get("LOG0/CNT/mod_cmd.xml?cmd=xml-counts")
    if response is None:
        return 1
    root_data = _get_element(response)
    if root_data is None:
        return 1

    informations = {}
    for entry in root_data:
        n = entry.get("n")
        x = entry.get("x")
        informations[n] = x

    for what in ["CPU", "MEM", "TEMP"]:
        if informations.get(what):
            section_name = "innovaphone_" + what.lower()
            get_informations(connection, section_name, informations[what], what)

    sys.stdout.writelines(
        f"{line}\n"
        for line in pri_channels_section(
            connection=connection,
            # TODO: do we really need to guess at the channels?!
            channels=("PRI1", "PRI2", "PRI3", "PRI4"),
        )
    )

    sys.stdout.writelines(f"{line}\n" for line in licenses_section(connection))
    return None


if __name__ == "__main__":
    sys.exit(main())
