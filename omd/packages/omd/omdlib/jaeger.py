#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from omdlib.config_api import Config, PortHook


def write_jaeger_receiver_conf(_site_name: str, site_home: Path, config: Config) -> None:
    address = config.get("TRACE_RECEIVE_ADDRESS", "0")
    port = config.get("TRACE_RECEIVE_PORT", "0")
    content = f"""\
# Written by TRACE_RECEIVE_ADDRESS or TRACE_RECEIVE_PORT hook
---
receivers:
    otlp:
        protocols:
            grpc:
                endpoint: "{address}:{port}"
"""
    with open(site_home / "etc" / "jaeger" / "omd-grpc.yaml", "w") as f:
        f.write(content)


def _write_jaeger_ui_port_conf(site_name: str, site_home: Path, config: Config) -> None:
    port = config["TRACE_JAEGER_UI_PORT"]
    apache_content = f"""\
# Written by TRACE_JAEGER_UI_PORT hook
LoadModule proxy_module /omd/sites/{site_name}/lib/apache/modules/mod_proxy.so
LoadModule proxy_http_module /omd/sites/{site_name}/lib/apache/modules/mod_proxy_http.so

ProxyPass "/{site_name}/jaeger" "http://[::1]:{port}/{site_name}/jaeger" retry=0 timeout=120
ProxyPassReverse "/{site_name}/jaeger"  "http://[::1]:{port}/{site_name}/jaeger"
"""
    with open(site_home / "etc" / "jaeger" / "apache.conf", "w") as f:
        f.write(apache_content)

    query_content = f"""\
# Written by TRACE_JAEGER_UI_PORT hook
---
extensions:
    jaeger_query:
        http:
            endpoint: "[::1]:{port}"
"""
    with open(site_home / "etc" / "jaeger" / "omd-query-port.yaml", "w") as f:
        f.write(query_content)


def _write_jaeger_admin_port_conf(_site_name: str, site_home: Path, config: Config) -> None:
    port = config["TRACE_JAEGER_ADMIN_PORT"]
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
    with open(site_home / "etc" / "jaeger" / "omd-admin-port.yaml", "w") as f:
        f.write(content)


TRACE_JAEGER_ADMIN_PORT_HOOK = PortHook(
    name="TRACE_JAEGER_ADMIN_PORT",
    display_name="The port",
    default_port=14269,
    activation=_write_jaeger_admin_port_conf,
)

TRACE_JAEGER_UI_PORT_HOOK = PortHook(
    name="TRACE_JAEGER_UI_PORT",
    display_name="The port",
    default_port=16686,
    activation=_write_jaeger_ui_port_conf,
)

TRACE_RECEIVE_PORT_HOOK = PortHook(
    name="TRACE_RECEIVE_PORT",
    display_name="Trace receiving port",
    default_port=4417,
    activation=write_jaeger_receiver_conf,
)
