#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import socket
import sys

# This special agent uses the S2A RCM API. Please refer to the
# official documentation.


def commandstring(command_txt, username_txt, password_txt):
    return "%s@%s@%s@0@0@$" % (command_txt, username_txt, password_txt)


def query(s, command_txt):
    s.sendall(command_txt)
    response = []
    while True:
        next_part = s.recv(2048)
        response.append(next_part)
        if not next_part:
            break
    return "".join(response)


def main(sys_argv=None):
    if sys_argv is None:
        sys_argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="A datasource program for Data Direct" "Networks Silicon Storage Appliances"
    )

    parser.add_argument("ip_address")
    parser.add_argument("port", type=int)
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args(sys_argv)
    _debug = args.debug
    ip_address = args.ip_address
    port = args.port
    username = args.username
    password = args.password

    sections = [
        ("1600", "ddn_s2a_faultsbasic"),
        ("1000", "ddn_s2a_version"),
        ("2500", "ddn_s2a_uptime"),
        ("2301", "ddn_s2a_statsdelay"),
        ("0505", "ddn_s2a_errors"),
        ("2300", "ddn_s2a_stats"),
    ]

    for command, section in sections:
        print("<<<%s>>>" % section)
        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        sock.connect((ip_address, port))
        print(query(sock, commandstring(command, username, password)))
        sock.close()
