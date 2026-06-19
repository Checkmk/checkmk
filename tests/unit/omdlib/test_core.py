#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

import pytest

from omdlib.core import CoreHasError, write_core_conf


def test_core_has_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    choices = CoreHasError()
    # "none" is always allowed; cmc/nagios only when their binary is present.
    assert choices("none").is_ok()
    assert choices("cmc").is_error()
    assert choices("nagios").is_error()

    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "cmc").write_text("")
    assert choices("cmc").is_ok()
    assert choices("nagios").is_error()


def _mkdirs(tmp_path: Path) -> None:
    (tmp_path / "etc/apache/conf.d").mkdir(parents=True)
    (tmp_path / "etc/check_mk/conf.d").mkdir(parents=True)
    (tmp_path / "etc/init.d").mkdir(parents=True)
    (tmp_path / "var/log").mkdir(parents=True)
    (tmp_path / "var/nagios").mkdir(parents=True)
    (tmp_path / "var/check_mk/core").mkdir(parents=True)


def _skeleton(tmp_path: Path) -> None:
    _mkdirs(tmp_path)
    (tmp_path / "etc/init.d/cmc").write_text("cmc")
    (tmp_path / "etc/init.d/nagios").write_text("nagios")


def test_write_core_conf_cmc(tmp_path: Path) -> None:
    _skeleton(tmp_path)
    write_core_conf("mysite", tmp_path, {"CORE": "nagios"})
    os.symlink("../apache2/x.conf", tmp_path / "etc/apache/conf.d/nagios.conf")
    (tmp_path / "var/check_mk/core/config").write_text("objects")

    write_core_conf("mysite", tmp_path, {"CORE": "cmc"})

    core_link = tmp_path / "etc/init.d/core"
    assert core_link.is_symlink()
    assert os.readlink(core_link) == "cmc"
    assert (tmp_path / "etc/check_mk/conf.d/microcore.mk").read_text() == (
        "# Created by OMD hook CORE. Change with 'omd config'.\nmonitoring_core = 'cmc'\n"
    )
    assert not (tmp_path / "etc/apache/conf.d/nagios.conf").exists()
    assert not (tmp_path / "var/check_mk/core/config").exists()
    assert not (tmp_path / "var/log/livestatus.log").exists()
    assert not (tmp_path / "var/log/nagios.log").exists()


def test_write_core_conf_nagios(tmp_path: Path) -> None:
    _skeleton(tmp_path)
    write_core_conf("mysite", tmp_path, {"CORE": "cmc"})
    (tmp_path / "etc/apache/conf.d/nagios.conf").write_text("regular\n")
    (tmp_path / "var/log/livestatus.log").write_text("real log\n")
    (tmp_path / "var/log/nagios.log").write_text("real log\n")

    write_core_conf("mysite", tmp_path, {"CORE": "nagios"})

    core_link = tmp_path / "etc/init.d/core"
    assert core_link.is_symlink()
    assert os.readlink(core_link) == "nagios"
    assert not (tmp_path / "etc/check_mk/conf.d/microcore.mk").exists()
    assert (tmp_path / "etc/apache/conf.d/nagios.conf").read_text() == "regular\n"
    assert os.readlink(tmp_path / "var/log/livestatus.log") == "../nagios/livestatus.log"
    assert os.readlink(tmp_path / "var/log/nagios.log") == "../nagios/nagios.log"


def test_write_core_conf_none(tmp_path: Path) -> None:
    _skeleton(tmp_path)
    write_core_conf("mysite", tmp_path, {"CORE": "cmc"})

    write_core_conf("mysite", tmp_path, {"CORE": "none"})

    assert not (tmp_path / "etc/init.d/core").exists()
    assert not (tmp_path / "etc/check_mk/conf.d/microcore.mk").exists()
    assert os.readlink(tmp_path / "var/log/livestatus.log") == "../nagios/livestatus.log"
    assert os.readlink(tmp_path / "var/log/nagios.log") == "../nagios/nagios.log"


def test_write_core_conf_missing_core_binary_skips_link(tmp_path: Path) -> None:
    _mkdirs(tmp_path)

    write_core_conf("mysite", tmp_path, {"CORE": "cmc"})

    assert not (tmp_path / "etc/init.d/core").exists()
    assert (tmp_path / "etc/check_mk/conf.d/microcore.mk").exists()
