#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from omdlib.liveproxyd import write_liveproxyd_conf


def test_write_liveproxyd_conf_on(tmp_path: Path) -> None:
    (tmp_path / "etc/check_mk/multisite.d").mkdir(parents=True)
    write_liveproxyd_conf("_", tmp_path, {"LIVEPROXYD": "on"})
    content = (tmp_path / "etc/check_mk/multisite.d/liveproxyd.mk").read_text()
    assert content == "liveproxyd_enabled = True\n"


def test_write_liveproxyd_conf_off(tmp_path: Path) -> None:
    (tmp_path / "etc/check_mk/multisite.d").mkdir(parents=True)
    write_liveproxyd_conf("_", tmp_path, {"LIVEPROXYD": "off"})
    content = (tmp_path / "etc/check_mk/multisite.d/liveproxyd.mk").read_text()
    assert content == "liveproxyd_enabled = False\n"
