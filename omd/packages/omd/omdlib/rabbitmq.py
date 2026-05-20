#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path


def write_rabbitmq_management_port_conf(omd_root: str, port: str) -> None:
    content = (
        "# Port set by `omd config` hook `RABBITMQ_MANAGEMENT_PORT`. Better do not edit manually.\n"
        f"management.ssl.port = {port}\n"
    )
    with open(Path(omd_root, "etc", "rabbitmq", "conf.d", "02-management-port.conf"), "w") as f:
        f.write(content)
