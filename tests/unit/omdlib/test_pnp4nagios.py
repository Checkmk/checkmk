#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

from omdlib.pnp4nagios import write_pnp4nagios_conf

_CFG = "etc/nagios/nagios.d/pnp4nagios.cfg"
_PERFDATA = "etc/mod-gearman/perfdata.conf"
_MK = "etc/check_mk/conf.d/pnp4nagios.mk"
_APACHE = "etc/apache/conf.d/pnp4nagios.conf"


def _skeleton(tmp_path: Path) -> None:
    (tmp_path / "etc/nagios/nagios.d").mkdir(parents=True)
    (tmp_path / "etc/mod-gearman").mkdir(parents=True)
    (tmp_path / "etc/check_mk/conf.d").mkdir(parents=True)
    (tmp_path / "etc/apache/conf.d").mkdir(parents=True)
    (tmp_path / _PERFDATA).write_text("perfdata=yes\nother=1\n")
    (tmp_path / _APACHE).write_text("old\n")


def test_pnp4nagios_on(tmp_path: Path) -> None:
    _skeleton(tmp_path)
    write_pnp4nagios_conf("_", tmp_path, {"PNP4NAGIOS": "on"})
    assert os.readlink(tmp_path / _CFG) == "../../pnp4nagios/nagios_npcdmod.cfg"
    assert (tmp_path / _PERFDATA).read_text() == "perfdata=no\nother=1\n"
    assert not (tmp_path / _APACHE).exists()
    assert (tmp_path / _MK).read_text() == (
        "# Set by OMD hook PNP4NAGIOS, do not change here!\npnp4nagios_enabled = True\n"
    )


def test_pnp4nagios_gearman(tmp_path: Path) -> None:
    _skeleton(tmp_path)
    write_pnp4nagios_conf("_", tmp_path, {"PNP4NAGIOS": "gearman"})
    assert os.readlink(tmp_path / _CFG) == "../../pnp4nagios/nagios_gearman.cfg"
    assert (tmp_path / _PERFDATA).read_text() == "perfdata=yes\nother=1\n"
    assert (tmp_path / _MK).read_text().endswith("pnp4nagios_enabled = True\n")


def test_pnp4nagios_npcd_leaves_perfdata_untouched(tmp_path: Path) -> None:
    _skeleton(tmp_path)
    write_pnp4nagios_conf("_", tmp_path, {"PNP4NAGIOS": "npcd"})
    assert os.readlink(tmp_path / _CFG) == "../../pnp4nagios/nagios_npcd.cfg"
    assert (tmp_path / _PERFDATA).read_text() == "perfdata=yes\nother=1\n"
    assert (tmp_path / _MK).read_text().endswith("pnp4nagios_enabled = True\n")


def test_pnp4nagios_off_removes_symlink_and_disables(tmp_path: Path) -> None:
    _skeleton(tmp_path)
    write_pnp4nagios_conf("_", tmp_path, {"PNP4NAGIOS": "on"})
    write_pnp4nagios_conf("_", tmp_path, {"PNP4NAGIOS": "off"})
    assert not (tmp_path / _CFG).exists()
    assert (tmp_path / _PERFDATA).read_text() == "perfdata=no\nother=1\n"
    assert (tmp_path / _MK).read_text().endswith("pnp4nagios_enabled = False\n")


def test_pnp4nagios_on_without_nagios_d_skips_symlink(tmp_path: Path) -> None:
    (tmp_path / "etc/check_mk/conf.d").mkdir(parents=True)
    write_pnp4nagios_conf("_", tmp_path, {"PNP4NAGIOS": "on"})
    assert not (tmp_path / _CFG).exists()
    assert (tmp_path / _MK).read_text().endswith("pnp4nagios_enabled = True\n")


def test_pnp4nagios_empty_perfdata_not_modified(tmp_path: Path) -> None:
    _skeleton(tmp_path)
    (tmp_path / _PERFDATA).write_text("")
    write_pnp4nagios_conf("_", tmp_path, {"PNP4NAGIOS": "on"})
    assert (tmp_path / _PERFDATA).read_text() == ""
