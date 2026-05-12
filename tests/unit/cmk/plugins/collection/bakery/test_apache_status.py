#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from pprint import pformat

from cmk.bakery.v2_unstable import OS, Plugin, PluginConfig
from cmk.plugins.collection.bakery.apache_status import bakery_plugin_apache_status


def test_apache_status_files_static() -> None:
    servers = [{"protocol": "http", "address": "127.0.0.1", "port": 80, "instance": "hurz"}]
    conf = bakery_plugin_apache_status.parameter_parser(
        {"deployment": ("sync", None), "instances": ("static", servers)}
    )
    result = sorted(bakery_plugin_apache_status.files_function(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("apache_status.py"), interval=None),
            PluginConfig(
                base_os=OS.LINUX,
                lines=["servers = %s" % pformat(servers)],
                target=Path("apache_status.cfg"),
                include_header=True,
            ),
        ],
        key=repr,
    )
    assert result == expected


def test_apache_status_files_autodetect() -> None:
    ssl_ports = [443]
    conf = bakery_plugin_apache_status.parameter_parser(
        {"deployment": ("sync", None), "instances": ("autodetect", ssl_ports)}
    )
    result = sorted(bakery_plugin_apache_status.files_function(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("apache_status.py"), interval=None),
            PluginConfig(
                base_os=OS.LINUX,
                lines=[f"ssl_ports = {ssl_ports!r}"],
                target=Path("apache_status.cfg"),
                include_header=True,
            ),
        ],
        key=repr,
    )
    assert result == expected


def test_apache_status_files_no_instances() -> None:
    conf = bakery_plugin_apache_status.parameter_parser({"deployment": ("sync", None)})
    result = list(bakery_plugin_apache_status.files_function(conf))
    assert result == [Plugin(base_os=OS.LINUX, source=Path("apache_status.py"), interval=None)]


def test_apache_status_files_do_not_deploy() -> None:
    conf = bakery_plugin_apache_status.parameter_parser({"deployment": ("do_not_deploy", None)})
    assert list(bakery_plugin_apache_status.files_function(conf)) == []
