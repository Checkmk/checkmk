#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path


def write_rabbitmq_default_conf(omd_root: str, only_from: str, port: str) -> None:
    lines = [
        "# Port and IP addresses set by `omd config` hooks `RABBITMQ_ONLY_FROM` and\n",
        "# `RABBITMQ_PORT`. Better do not edit manually.\n",
        *(
            f"listeners.ssl.{i} = {addr}:{port}\n"
            for i, addr in enumerate(only_from.split(), start=1)
        ),
    ]
    with open(Path(omd_root, "etc", "rabbitmq", "conf.d", "01-default.conf"), "w") as f:
        f.write("".join(lines))


def write_rabbitmq_management_port_conf(omd_root: str, port: str) -> None:
    content = f"""\
# Port set by `omd config` hook `RABBITMQ_MANAGEMENT_PORT`. Better do not edit manually.
management.ssl.port = {port}
"""
    with open(Path(omd_root, "etc", "rabbitmq", "conf.d", "02-management-port.conf"), "w") as f:
        f.write(content)
