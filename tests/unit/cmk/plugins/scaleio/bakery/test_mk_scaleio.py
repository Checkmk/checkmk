#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v2 import OS, Plugin, PluginConfig, Secret
from cmk.plugins.scaleio.bakery.mk_scaleio import bakery_plugin_mk_scaleio, get_mk_scaleio_files

_PASSWORD = Secret("secret123", "explicit_password", "uuid-1")


def test_mk_scaleio_files_sync() -> None:
    conf = {"deployment": ("sync", None), "user": "admin", "password": _PASSWORD}
    assert sorted(
        get_mk_scaleio_files(bakery_plugin_mk_scaleio.parameter_parser(conf)), key=repr
    ) == sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("mk_scaleio"), interval=None),
            PluginConfig(
                base_os=OS.LINUX,
                lines=["SIO_USER=admin", "SIO_PASSWORD=secret123"],
                target=Path("mk_scaleio.cfg"),
                include_header=True,
            ),
        ],
        key=repr,
    )


def test_mk_scaleio_files_cached() -> None:
    conf = {"deployment": ("cached", 120.0), "user": "admin", "password": _PASSWORD}
    plugin = [
        r
        for r in get_mk_scaleio_files(bakery_plugin_mk_scaleio.parameter_parser(conf))
        if isinstance(r, Plugin)
    ][0]
    assert plugin.interval == 120


def test_mk_scaleio_files_do_not_deploy() -> None:
    assert (
        list(
            get_mk_scaleio_files(
                bakery_plugin_mk_scaleio.parameter_parser({"deployment": ("do_not_deploy", None)})
            )
        )
        == []
    )
