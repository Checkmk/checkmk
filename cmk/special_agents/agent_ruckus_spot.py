#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import getopt
import socket
import sys
from typing import NoReturn

import requests


def usage() -> NoReturn:
    sys.stderr.write(
        """Check_MK Ruckus Spot Agent

USAGE: agent_ruckus_spot [OPTIONS] HOST

OPTIONS:
  -h, --help                    Show this help message and exit
  --address                     Address {hostname:port}
  --venueid                     Venue ID
  --apikey                      API key
"""
    )
    sys.exit(1)


# TODO: put into special_agent lib
def get_agent_info_tcp(host: str) -> bytes:
    ipaddress = socket.gethostbyname(host)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect((ipaddress, 6556))

    try:
        s.setblocking(True)
    except Exception:
        pass

    resp = b""
    while True:
        out = s.recv(4096, socket.MSG_WAITALL)
        if out and len(out) > 0:
            resp += out
        else:
            break
    s.close()
    return resp


def main(sys_argv=None):
    if sys_argv is None:
        sys_argv = sys.argv[1:]

    short_options = "h:"
    long_options = ["help", "address=", "venueid=", "apikey=", "agent_port="]

    address = None
    venueid = None
    api_key = None
    agent_port = None

    try:
        opts, args = getopt.getopt(sys_argv, short_options, long_options)
    except getopt.GetoptError as err:
        sys.stderr.write("%s\n" % err)
        return 1

    for o, a in opts:
        if o in ["--address"]:
            address = a
        elif o in ["--venueid"]:
            venueid = a
        elif o in ["--apikey"]:
            api_key = a
        elif o in ["--agent_port"]:
            agent_port = a
        elif o in ["-h", "--help"]:
            usage()

    if len(args) > 0 or not api_key or not venueid or not address:
        usage()

    try:
        for url_end, section_type in [
            ("access_points/statuses.json", "ap"),
            ("locations/last_known.json", "locations"),
        ]:
            url = "http://%(address)s/api/v1/venues/%(venueid)s/%(url_end)s" % {
                "address": address,
                "venueid": venueid,
                "url_end": url_end,
            }
            response = requests.get(url, auth=(api_key, "X"))

            sys.stdout.write("<<<ruckus_spot_%s:sep(0)>>>\n" % section_type)
            sys.stdout.write(response.text + "\n")

        if agent_port is not None:
            hostname = address.split(":")[0]
            sys.stdout.write(get_agent_info_tcp(hostname).decode())

    except Exception as e:
        sys.stderr.write("Connection error %s" % e)
        return 1
