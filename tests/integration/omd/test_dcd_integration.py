#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess

from tests.testlib.pytest_helpers.marks import skip_if_raw_edition
from tests.testlib.site import Site


@skip_if_raw_edition
def test_dcd_exists(site: Site) -> None:
    assert site.file_exists("bin/dcd")


@skip_if_raw_edition
def test_dcd_path(site: Site) -> None:
    p = site.execute(["which", "dcd"], stdout=subprocess.PIPE)
    path = p.stdout.read().strip() if p.stdout else "<NO STDOUT>"
    assert path == "/omd/sites/%s/bin/dcd" % site.id


@skip_if_raw_edition
def test_dcd_version(site: Site) -> None:
    p = site.execute(["dcd", "-V"], stdout=subprocess.PIPE)
    version = p.stdout.read() if p.stdout else "<NO STDOUT>"
    assert version.startswith("dcd version %s" % site.version.version)


@skip_if_raw_edition
def test_dcd_daemon(site: Site) -> None:
    p = site.omd("status", "--bare", "dcd", check=True)
    assert p.stdout == "dcd 0\nOVERALL 0\n" if p.stdout else False


@skip_if_raw_edition
def test_dcd_logrotate(site: Site) -> None:
    assert site.file_exists("etc/logrotate.d/dcd")
