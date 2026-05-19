#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path


def write_jaeger_receiver_conf(omd_root: str, address: str, port: str) -> None:
    content = f"""\
# Written by TRACE_RECEIVE_ADDRESS or TRACE_RECEIVE_PORT hook
---
receivers:
    otlp:
        protocols:
            grpc:
                endpoint: "{address}:{port}"
"""
    with open(Path(omd_root, "etc", "jaeger", "omd-grpc.yaml"), "w") as f:
        f.write(content)


def write_jaeger_ui_port_conf(omd_root: str, site_name: str, port: str) -> None:
    apache_content = f"""\
# Written by TRACE_JAEGER_UI_PORT hook
LoadModule proxy_module /omd/sites/{site_name}/lib/apache/modules/mod_proxy.so
LoadModule proxy_http_module /omd/sites/{site_name}/lib/apache/modules/mod_proxy_http.so

ProxyPass "/{site_name}/jaeger" "http://[::1]:{port}/{site_name}/jaeger" retry=0 timeout=120
ProxyPassReverse "/{site_name}/jaeger"  "http://[::1]:{port}/{site_name}/jaeger"
"""
    with open(Path(omd_root, "etc", "jaeger", "apache.conf"), "w") as f:
        f.write(apache_content)

    query_content = f"""\
# Written by TRACE_JAEGER_UI_PORT hook
---
extensions:
    jaeger_query:
        http:
            endpoint: "[::1]:{port}"
"""
    with open(Path(omd_root, "etc", "jaeger", "omd-query-port.yaml"), "w") as f:
        f.write(query_content)


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
