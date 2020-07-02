#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
import omdlib.tmpfs
from omdlib.tmpfs import add_to_fstab


@pytest.fixture(name="tmp_fstab")
def fixture_tmp_fstab(tmp_path, monkeypatch):
    fstab_path = tmp_path / "fstab"
    monkeypatch.setattr(omdlib.tmpfs, "fstab_path", lambda: str(fstab_path))
    return fstab_path


@pytest.mark.usefixtures("site_context")
def test_add_to_fstab_not_existing(tmp_fstab, site_context):
    assert not tmp_fstab.exists()
    add_to_fstab(site_context)
    assert not tmp_fstab.exists()


def test_add_to_fstab(tmp_fstab, site_context):
    tmp_fstab.open("w", encoding="utf-8").write(u"# system fstab bla\n")
    add_to_fstab(site_context)
    assert tmp_fstab.open().read() == (
        "# system fstab bla\n"
        "tmpfs  /opt/omd/sites/unit/tmp tmpfs noauto,user,mode=755,uid=unit,gid=unit 0 0\n")


def test_add_to_fstab_with_size(tmp_fstab, site_context):
    tmp_fstab.open("w", encoding="utf-8").write(u"# system fstab bla\n")
    add_to_fstab(site_context, tmpfs_size="1G")
    assert tmp_fstab.open().read() == (
        "# system fstab bla\n"
        "tmpfs  /opt/omd/sites/unit/tmp tmpfs noauto,user,mode=755,uid=unit,gid=unit,size=1G 0 0\n")


def test_add_to_fstab_no_newline_at_end(tmp_fstab, site_context):
    tmp_fstab.open("w", encoding="utf-8").write(u"# system fstab bla")
    add_to_fstab(site_context)
    assert tmp_fstab.open().read() == (
        "# system fstab bla\n"
        "tmpfs  /opt/omd/sites/unit/tmp tmpfs noauto,user,mode=755,uid=unit,gid=unit 0 0\n")


def test_add_to_fstab_empty(tmp_fstab, site_context):
    tmp_fstab.open("w", encoding="utf-8").write(u"")
    add_to_fstab(site_context)
    assert tmp_fstab.open().read() == (
        "tmpfs  /opt/omd/sites/unit/tmp tmpfs noauto,user,mode=755,uid=unit,gid=unit 0 0\n")
