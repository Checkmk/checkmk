#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v1 import OS, Plugin, PluginConfig
from cmk.base.plugins.bakery.mk_scaleio import get_mk_scaleio_files, ScaleioConfig


def test_mk_scaleio_files_default_interval() -> None:
    conf = ScaleioConfig(user="admin", password=("password", "secret123"))
    result = sorted(get_mk_scaleio_files(conf), key=repr)
    expected = sorted(
        [
            Plugin(base_os=OS.LINUX, source=Path("mk_scaleio"), interval=0),
            PluginConfig(
                base_os=OS.LINUX,
                lines=["SIO_USER=admin", "SIO_PASSWORD=secret123"],
                target=Path("mk_scaleio.cfg"),
                include_header=True,
            ),
        ],
        key=repr,
    )
    assert result == expected


def test_mk_scaleio_files_interval_below_60() -> None:
    """Interval <= 60 is reset to 0."""
    conf = ScaleioConfig(user="admin", password=("password", "secret"), interval=30)
    result = sorted(get_mk_scaleio_files(conf), key=repr)
    plugin = [r for r in result if isinstance(r, Plugin)][0]
    assert plugin.interval == 0


def test_mk_scaleio_files_interval_above_60() -> None:
    conf = ScaleioConfig(user="admin", password=("password", "secret"), interval=120)
    result = sorted(get_mk_scaleio_files(conf), key=repr)
    plugin = [r for r in result if isinstance(r, Plugin)][0]
    assert plugin.interval == 120


def test_mk_scaleio_files_interval_exact_60() -> None:
    """Interval exactly 60 is still reset to 0."""
    conf = ScaleioConfig(user="admin", password=("password", "secret"), interval=60)
    result = sorted(get_mk_scaleio_files(conf), key=repr)
    plugin = [r for r in result if isinstance(r, Plugin)][0]
    assert plugin.interval == 0
