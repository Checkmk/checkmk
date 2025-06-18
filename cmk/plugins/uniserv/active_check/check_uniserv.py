#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import socket
import sys
from collections.abc import Mapping


def parse_response(data: str) -> Mapping[str, str]:
    try:
        parsed = dict([x.split("=") for x in data.split(";")][:-1])
        if parsed["type"] == "1":
            bail_out(3, f"Invalid response: {data!r}")
    except (ValueError, KeyError):
        bail_out(3, f"Invalid data: {data!r}")

    return parsed


def send_and_receive(sock: socket.socket, request_str: str) -> Mapping[str, str]:
    sock.send(f"{request_str}\n".encode())
    return parse_response(sock.recv(1024).decode())


def check_job(
    job: str,
    tcp_socket: socket.socket,
    sid: str,
    street: str,
    street_nr: str,
    city: str,
    regex: str,
) -> tuple[int, str]:
    if job == "VERSION":
        data = send_and_receive(tcp_socket, f"version:session={sid}")
        try:
            return 0, f"Version: {data['version_str']}"
        except KeyError:
            return 3, "Unknown version"

    if job == "ADDRESS":
        _data = send_and_receive(
            tcp_socket,
            f"exec:session={sid};request_type=check_address;in_str={street};"
            f"in_hno={street_nr};in_city={city}",
        )

        data = send_and_receive(tcp_socket, f"fetch:session={sid};out_zip=?;out_city=?")

        try:
            infotext = f"Address: {data['out_zip']} {data['out_city']}"
        except KeyError:
            return 3, "Unknown zip or city"

        if re.match(regex, data["out_city"]):
            return 0, infotext

        return 2, f"{infotext} but expects {regex}"

    return 3, "Unknown job"


def parse_arguments(sys_args):
    if sys_args is None:
        sys_args = sys.argv[1:]

    host = None
    tcp_port = None
    service = None
    job = None
    street = None
    street_nr = None
    city = None
    regex = None
    try:
        host = sys_args[0]
        tcp_port = int(sys_args[1])
        service = sys_args[2]
        job = sys_args[3]
        if job == "ADDRESS":
            street = sys_args[4]
            street_nr = sys_args[5]
            city = sys_args[6]
            regex = sys_args[7]
    except (IndexError, ValueError):
        bail_out(
            3,
            (
                "usage: check_uniserv HOSTNAME PORT SERVICE"
                " (VERSION|ADDRESS STREET NR CITY SEARCH_REGEX)"
            ),
        )

    return host, tcp_port, service, job, street, street_nr, city, regex


def bail_out(result: int, message: str) -> None:
    sys.stdout.write(f"{message}\n")
    raise SystemExit(result)


def main(sys_args=None):
    host, tcp_port, service, job, street, street_nr, city, regex = parse_arguments(sys_args)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.connect((host, tcp_port))

        data = send_and_receive(tcp_socket, f"open:service={service};servicehost={host}")
        if not (sid := data.get("session")):
            return 3, f"Error getting SID. Response was: {data}"

        state, infotext = check_job(job, tcp_socket, sid, street, street_nr, city, regex)

        tcp_socket.send(f"close:session={sid}\n".encode())

    sys.stdout.write(f"{infotext}\n")
    return state
