#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v2_unstable import OS, Plugin, PluginConfig
from cmk.plugins.ceph.bakery.ceph import bakery_plugin_ceph


def test_get_ceph_files_no_deploy() -> None:
    # TODO: Consider making files functions etc not-None
    # to avoid conditions in code and assertions in tests.
    assert bakery_plugin_ceph.files_function is not None
    assert not list(
        bakery_plugin_ceph.files_function(
            bakery_plugin_ceph.parameter_parser({"deploy": False, "interval": ("cached", 58.0)})
        )
    )


def test_get_ceph_files_interval_uncached() -> None:
    assert bakery_plugin_ceph.files_function is not None
    assert list(
        bakery_plugin_ceph.files_function(
            bakery_plugin_ceph.parameter_parser({"deploy": True, "interval": ("uncached", None)})
        )
    ) == [
        Plugin(
            base_os=OS.LINUX,
            source=Path("mk_ceph.py"),
            interval=None,
        )
    ]


def test_get_ceph_files_interval_cached() -> None:
    assert bakery_plugin_ceph.files_function is not None
    assert list(
        bakery_plugin_ceph.files_function(
            bakery_plugin_ceph.parameter_parser({"deploy": True, "interval": ("cached", 123.0)})
        )
    ) == [
        Plugin(
            base_os=OS.LINUX,
            source=Path("mk_ceph.py"),
            interval=123,
        )
    ]


def test_get_ceph_files_config() -> None:
    assert bakery_plugin_ceph.files_function is not None
    assert list(
        bakery_plugin_ceph.files_function(
            bakery_plugin_ceph.parameter_parser(
                {"deploy": True, "interval": ("cached", 58.0), "config": "foo"}
            )
        )
    ) == [
        Plugin(
            base_os=OS.LINUX,
            source=Path("mk_ceph.py"),
            interval=58,
        ),
        PluginConfig(
            base_os=OS.LINUX,
            lines=["CONFIG=foo"],
            target=Path("ceph.cfg"),
            include_header=True,
        ),
    ]


def test_get_ceph_files_client() -> None:
    assert bakery_plugin_ceph.files_function is not None
    assert list(
        bakery_plugin_ceph.files_function(
            bakery_plugin_ceph.parameter_parser(
                {"deploy": True, "interval": ("cached", 58.0), "client": "foo"}
            )
        )
    ) == [
        Plugin(
            base_os=OS.LINUX,
            source=Path("mk_ceph.py"),
            interval=58,
        ),
        PluginConfig(
            base_os=OS.LINUX,
            lines=["CLIENT=foo"],
            target=Path("ceph.cfg"),
            include_header=True,
        ),
    ]
