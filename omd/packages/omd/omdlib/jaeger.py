#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
from pathlib import Path

from omdlib.config_api import (
    Config,
    Hook,
    ip_address_list_has_error,
    network_port_has_error,
    null_action,
    PortHook,
)


def write_jaeger_apache_conf(_site_name: str, site_home: Path, config: Config) -> None:
    # Toggle the apache reverse proxy for accessing the Jaeger UI
    jaeger_conf = site_home / "etc" / "apache" / "conf.d" / "jaeger.conf"
    if config["TRACE_RECEIVE"] == "on":
        jaeger_conf.unlink(missing_ok=True)
        os.symlink("../../jaeger/apache.conf", jaeger_conf)
    elif jaeger_conf.is_file():
        jaeger_conf.unlink()


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


TRACE_JAEGER_ADMIN_PORT = PortHook(
    name="TRACE_JAEGER_ADMIN_PORT",
    display_name="The port",
    default_port=14269,
    activation=_write_jaeger_admin_port_conf,
    choices=network_port_has_error,
    depends=lambda c: c.get("TRACE_RECEIVE") == "on",
)

TRACE_JAEGER_UI_PORT = PortHook(
    name="TRACE_JAEGER_UI_PORT",
    display_name="The port",
    default_port=16686,
    activation=_write_jaeger_ui_port_conf,
    choices=network_port_has_error,
    depends=lambda c: c.get("TRACE_RECEIVE") == "on",
)

TRACE_RECEIVE = Hook(
    name="TRACE_RECEIVE",
    choices=[("on", "enable"), ("off", "disable")],
    default=lambda _edition: "off",
    activation=write_jaeger_apache_conf,
)

TRACE_RECEIVE_ADDRESS = Hook(
    name="TRACE_RECEIVE_ADDRESS",
    choices=ip_address_list_has_error,
    default=lambda _edition: "[::1]",
    depends=lambda c: c.get("TRACE_RECEIVE") == "on",
    activation=write_jaeger_receiver_conf,
)

TRACE_RECEIVE_PORT = PortHook(
    name="TRACE_RECEIVE_PORT",
    display_name="Trace receiving port",
    default_port=4417,
    activation=write_jaeger_receiver_conf,
    choices=network_port_has_error,
    depends=lambda c: c.get("TRACE_RECEIVE") == "on",
)

TRACE_SEND = Hook(
    name="TRACE_SEND",
    choices=[("on", "enable"), ("off", "disable")],
    default=lambda _edition: "off",
    activation=null_action,
)

TRACE_SEND_TARGET = Hook(
    name="TRACE_SEND_TARGET",
    choices=re.compile(r"^(local_site|https?://[^\:]+:[0-9]{4,5})$$"),
    default=lambda _edition: "local_site",
    depends=lambda c: c.get("TRACE_SEND") == "on",
    activation=null_action,
)

TRACE_SERVICE_NAMESPACE = Hook(
    name="TRACE_SERVICE_NAMESPACE",
    choices=re.compile(r"^[a-zA-Z0-9_\.-]*$$"),
    default=lambda _edition: "",
    depends=lambda c: c.get("TRACE_SEND") == "on",
    activation=null_action,
)
