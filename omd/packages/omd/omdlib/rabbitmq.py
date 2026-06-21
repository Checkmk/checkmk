#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from pathlib import Path

from omdlib.config_api import Config, Hook, ip_address_list_has_error, null_action, PortHook


def write_rabbitmq_default_conf(_site_name: str, site_home: Path, config: Config) -> None:
    only_from = config.get("RABBITMQ_ONLY_FROM", ":: 0.0.0.0")
    port = config.get("RABBITMQ_PORT", "5672")
    lines = [
        "# Port and IP addresses set by `omd config` hooks `RABBITMQ_ONLY_FROM` and\n",
        "# `RABBITMQ_PORT`. Better do not edit manually.\n",
        *(
            f"listeners.ssl.{i} = {addr}:{port}\n"
            for i, addr in enumerate(only_from.split(), start=1)
        ),
    ]
    with open(site_home / "etc" / "rabbitmq" / "conf.d" / "01-default.conf", "w") as f:
        f.write("".join(lines))


def _write_rabbitmq_management_port_conf(_site_name: str, site_home: Path, config: Config) -> None:
    port = config["RABBITMQ_MANAGEMENT_PORT"]
    content = f"""\
# Port set by `omd config` hook `RABBITMQ_MANAGEMENT_PORT`. Better do not edit manually.
management.ssl.port = {port}
"""
    with open(site_home / "etc" / "rabbitmq" / "conf.d" / "02-management-port.conf", "w") as f:
        f.write(content)


RABBITMQ_DIST_PORT = PortHook(
    name="RABBITMQ_DIST_PORT",
    display_name="RabbitMQ distribution port",
    default_port=25672,
    activation=null_action,
    choices=re.compile(r"[0-9]{1,5}$"),
)

RABBITMQ_MANAGEMENT_PORT = PortHook(
    name="RABBITMQ_MANAGEMENT_PORT",
    display_name="RabbitMQ management port",
    default_port=15671,
    activation=_write_rabbitmq_management_port_conf,
    choices=re.compile(r"[0-9]{1,5}$"),
)

RABBITMQ_ONLY_FROM = Hook(
    name="RABBITMQ_ONLY_FROM",
    choices=ip_address_list_has_error,
    default=lambda _edition: ":: 0.0.0.0",
    activation=write_rabbitmq_default_conf,
)

RABBITMQ_PORT = PortHook(
    name="RABBITMQ_PORT",
    display_name="RabbitMQ port",
    default_port=5672,
    activation=write_rabbitmq_default_conf,
    choices=re.compile(r"[0-9]{1,5}$"),
)
