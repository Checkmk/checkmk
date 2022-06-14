#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess

import pytest

from tests.testlib.site import Site

import cmk.utils.version as cmk_version


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="No dcd in raw edition")
def test_dcd_exists(site: Site) -> None:
    assert site.file_exists("bin/dcd")


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="No dcd in raw edition")
def test_dcd_path(site: Site) -> None:
    p = site.execute(["which", "dcd"], stdout=subprocess.PIPE)
    path = p.stdout.read().strip() if p.stdout else "<NO STDOUT>"
    assert path == "/omd/sites/%s/bin/dcd" % site.id


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="No dcd in raw edition")
def test_dcd_version(site: Site) -> None:
    p = site.execute(["dcd", "-V"], stdout=subprocess.PIPE)
    version = p.stdout.read() if p.stdout else "<NO STDOUT>"
    assert version.startswith("dcd version %s" % site.version.version)


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="No dcd in raw edition")
def test_dcd_daemon(site: Site) -> None:
    p = site.execute(["omd", "status", "--bare", "dcd"], stdout=subprocess.PIPE)
    assert p.wait() == 0
    assert p.stdout.read() == "dcd 0\nOVERALL 0\n" if p.stdout else False


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="No dcd in raw edition")
def test_dcd_logrotate(site: Site) -> None:
    assert site.file_exists("etc/logrotate.d/dcd")
