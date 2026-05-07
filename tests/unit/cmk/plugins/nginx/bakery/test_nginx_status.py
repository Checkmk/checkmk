#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from pprint import pformat

from cmk.bakery.v2_unstable import OS, Plugin, PluginConfig
from cmk.plugins.nginx.bakery.nginx_status import bakery_plugin_nginx_status


def test_nginx_status_files_static() -> None:
    servers = [{"protocol": "http", "address": "127.0.0.1", "port": 80}]
    conf = bakery_plugin_nginx_status.parameter_parser(
        {"deployment": ("sync", None), "instances": ("static", servers)}
    )
    result = sorted(bakery_plugin_nginx_status.files_function(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("nginx_status.py"), interval=None),
            PluginConfig(
                base_os=OS.LINUX,
                lines=["servers = %s" % pformat(servers)],
                target=Path("nginx_status.cfg"),
                include_header=True,
            ),
        ],
        key=repr,
    )
    assert result == expected


def test_nginx_status_files_autodetect() -> None:
    ssl_ports = [443, 8443]
    conf = bakery_plugin_nginx_status.parameter_parser(
        {"deployment": ("sync", None), "instances": ("autodetect", ssl_ports)}
    )
    result = sorted(bakery_plugin_nginx_status.files_function(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("nginx_status.py"), interval=None),
            PluginConfig(
                base_os=OS.LINUX,
                lines=["ssl_ports = %r" % ssl_ports],
                target=Path("nginx_status.cfg"),
                include_header=True,
            ),
        ],
        key=repr,
    )
    assert result == expected


def test_nginx_status_files_no_instances() -> None:
    conf = bakery_plugin_nginx_status.parameter_parser({"deployment": ("sync", None)})
    result = list(bakery_plugin_nginx_status.files_function(conf))
    assert result == [Plugin(base_os=OS.LINUX, source=Path("nginx_status.py"), interval=None)]


def test_nginx_status_files_do_not_deploy() -> None:
    conf = bakery_plugin_nginx_status.parameter_parser({"deployment": ("do_not_deploy", None)})
    assert list(bakery_plugin_nginx_status.files_function(conf)) == []
