#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path


def write_jaeger_admin_port_conf(omd_root: str, port: str) -> None:
    content = f"""\
# Written by TRACE_JAEGER_ADMIN_PORT hook
---
service:
    telemetry:
        metrics:
            level: detailed
            readers:
              - pull:
                  exporter:
                    prometheus:
                      host: "[::1]"
                      port: {port}
"""
    with open(Path(omd_root, "etc", "jaeger", "omd-admin-port.yaml"), "w") as f:
        f.write(content)
