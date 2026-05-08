#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v2_unstable import OS, Plugin, PluginConfig
from cmk.plugins.collection.bakery.dnsclient import bakery_plugin_dnsclient

CONFIG_LINES = [
    "# Hostnames to test resolver with",
    "HOSTADDRESSES='dummy1 dummy2'",
]


def test_dnsclient_deploy_without_hostnames() -> None:
    conf = bakery_plugin_dnsclient.parameter_parser({"deployment": ("sync", None)})
    result = list(bakery_plugin_dnsclient.files_function(conf))
    assert result == [
        Plugin(base_os=OS.LINUX, source=Path("dnsclient"), interval=None),
        Plugin(base_os=OS.SOLARIS, source=Path("dnsclient"), interval=None),
        Plugin(base_os=OS.AIX, source=Path("dnsclient"), interval=None),
    ]


def test_dnsclient_deploy_with_hostnames() -> None:
    conf = bakery_plugin_dnsclient.parameter_parser(
        {"deployment": ("sync", None), "hostnames": ["dummy1", "dummy2"]}
    )
    result = list(bakery_plugin_dnsclient.files_function(conf))
    assert result == [
        Plugin(base_os=OS.LINUX, source=Path("dnsclient"), interval=None),
        Plugin(base_os=OS.SOLARIS, source=Path("dnsclient"), interval=None),
        Plugin(base_os=OS.AIX, source=Path("dnsclient"), interval=None),
        PluginConfig(
            base_os=OS.LINUX,
            lines=CONFIG_LINES,
            target=Path("dnsclient.cfg"),
            include_header=True,
        ),
        PluginConfig(
            base_os=OS.SOLARIS,
            lines=CONFIG_LINES,
            target=Path("dnsclient.cfg"),
            include_header=True,
        ),
        PluginConfig(
            base_os=OS.AIX,
            lines=CONFIG_LINES,
            target=Path("dnsclient.cfg"),
            include_header=True,
        ),
    ]


def test_dnsclient_do_not_deploy() -> None:
    conf = bakery_plugin_dnsclient.parameter_parser({"deployment": ("do_not_deploy", None)})
    assert list(bakery_plugin_dnsclient.files_function(conf)) == []


def test_dnsclient_cached_with_hostnames() -> None:
    conf = bakery_plugin_dnsclient.parameter_parser(
        {"deployment": ("cached", 3600.0), "hostnames": ["dummy1"]}
    )
    result = list(bakery_plugin_dnsclient.files_function(conf))
    assert result == [
        Plugin(base_os=OS.LINUX, source=Path("dnsclient"), interval=3600.0),
        Plugin(base_os=OS.SOLARIS, source=Path("dnsclient"), interval=3600.0),
        Plugin(base_os=OS.AIX, source=Path("dnsclient"), interval=3600.0),
        PluginConfig(
            base_os=OS.LINUX,
            lines=["# Hostnames to test resolver with", "HOSTADDRESSES=dummy1"],
            target=Path("dnsclient.cfg"),
            include_header=True,
        ),
        PluginConfig(
            base_os=OS.SOLARIS,
            lines=["# Hostnames to test resolver with", "HOSTADDRESSES=dummy1"],
            target=Path("dnsclient.cfg"),
            include_header=True,
        ),
        PluginConfig(
            base_os=OS.AIX,
            lines=["# Hostnames to test resolver with", "HOSTADDRESSES=dummy1"],
            target=Path("dnsclient.cfg"),
            include_header=True,
        ),
    ]
