#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from omdlib.mkeventd import write_mkeventd_conf


def _mkdirs(tmp_path: Path) -> None:
    (tmp_path / "etc/check_mk/multisite.d").mkdir(parents=True)
    (tmp_path / "etc/check_mk/conf.d").mkdir(parents=True)


def test_write_mkeventd_conf_on(tmp_path: Path) -> None:
    _mkdirs(tmp_path)
    write_mkeventd_conf("mysite", tmp_path, {"MKEVENTD": "on"})
    expected = "# Set by OMD hook MKEVENTD, do not change here!\nmkeventd_enabled = True\n"
    assert (tmp_path / "etc/check_mk/multisite.d/mkeventd.mk").read_text() == expected
    assert (tmp_path / "etc/check_mk/conf.d/mkeventd.mk").read_text() == expected


def test_write_mkeventd_conf_off(tmp_path: Path) -> None:
    _mkdirs(tmp_path)
    write_mkeventd_conf("mysite", tmp_path, {"MKEVENTD": "off"})
    expected = "# Set by OMD hook MKEVENTD, do not change here!\nmkeventd_enabled = False\n"
    assert (tmp_path / "etc/check_mk/multisite.d/mkeventd.mk").read_text() == expected
    assert (tmp_path / "etc/check_mk/conf.d/mkeventd.mk").read_text() == expected


def test_write_mkeventd_conf_overwrites(tmp_path: Path) -> None:
    _mkdirs(tmp_path)
    write_mkeventd_conf("mysite", tmp_path, {"MKEVENTD": "on"})
    expected_on = "# Set by OMD hook MKEVENTD, do not change here!\nmkeventd_enabled = True\n"
    assert (tmp_path / "etc/check_mk/multisite.d/mkeventd.mk").read_text() == expected_on
    assert (tmp_path / "etc/check_mk/conf.d/mkeventd.mk").read_text() == expected_on

    write_mkeventd_conf("mysite", tmp_path, {"MKEVENTD": "off"})
    expected_off = "# Set by OMD hook MKEVENTD, do not change here!\nmkeventd_enabled = False\n"
    assert (tmp_path / "etc/check_mk/multisite.d/mkeventd.mk").read_text() == expected_off
    assert (tmp_path / "etc/check_mk/conf.d/mkeventd.mk").read_text() == expected_off
