#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

from omdlib.nagvis import write_nagvis_apache_conf


def _nagvis_conf(site_home: Path) -> Path:
    (site_home / "etc/apache/conf.d").mkdir(parents=True)
    return site_home / "etc/apache/conf.d/nagvis.conf"


def test_write_nagvis_apache_conf_on_links_nagvis_apache_conf(tmp_path: Path) -> None:
    nagvis_conf = _nagvis_conf(tmp_path)

    write_nagvis_apache_conf("_", tmp_path, {"NAGVIS": "on"})

    assert os.readlink(nagvis_conf) == "../../nagvis/apache.conf"


def test_write_nagvis_apache_conf_on_twice_keeps_link(tmp_path: Path) -> None:
    nagvis_conf = _nagvis_conf(tmp_path)

    write_nagvis_apache_conf("_", tmp_path, {"NAGVIS": "on"})
    write_nagvis_apache_conf("_", tmp_path, {"NAGVIS": "on"})

    assert os.readlink(nagvis_conf) == "../../nagvis/apache.conf"


def test_write_nagvis_apache_conf_off_removes_dangling_link(tmp_path: Path) -> None:
    nagvis_conf = _nagvis_conf(tmp_path)
    os.symlink("../../nagvis/apache.conf", nagvis_conf)

    write_nagvis_apache_conf("_", tmp_path, {"NAGVIS": "off"})

    assert not nagvis_conf.is_symlink()
