#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess

from tests.testlib.site import Site


def test_run_omd(site: Site) -> None:
    p = site.execute(["omd"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert p.wait() == 1
    assert stderr == ""
    assert "Usage" in stdout
    assert "omd COMMAND -h" in stdout


def test_run_omd_help(site: Site) -> None:
    p = site.execute(["omd", "help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert p.wait() == 0
    assert stderr == ""
    assert "Usage" in stdout
    assert "omd COMMAND -h" in stdout


def test_run_omd_version(site: Site) -> None:
    p = site.execute(["omd", "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert p.wait() == 0
    assert stderr == ""
    assert stdout.endswith("%s\n" % site.version.omd_version())


def test_run_omd_version_bare(site: Site) -> None:
    p = site.execute(["omd", "version", "-b"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert p.wait() == 0
    assert stderr == ""
    assert stdout.rstrip("\n") == site.version.omd_version()


def test_run_omd_versions(site: Site) -> None:
    p = site.execute(["omd", "versions"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert p.wait() == 0
    assert stderr == ""
    versions = [v.split(" ", 1)[0] for v in stdout.split("\n")]
    assert len(versions) >= 1
    assert site.version.omd_version() in versions


def test_run_omd_versions_bare(site: Site) -> None:
    p = site.execute(["omd", "versions", "-b"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert p.wait() == 0
    assert stderr == ""
    versions = stdout.split("\n")
    assert len(versions) >= 1
    assert site.version.omd_version() in versions


def test_run_omd_sites(site: Site) -> None:
    p = site.execute(["omd", "sites"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert p.wait() == 0
    assert stderr == ""
    assert site.id in stdout


def test_run_omd_sites_bare(site: Site) -> None:
    p = site.execute(["omd", "sites", "-b"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert p.wait() == 0
    assert stderr == ""
    sites = stdout.split("\n")
    assert len(sites) >= 1
    assert site.id in sites


# TODO: Add tests for these modes (also check -h of each mode)
# omd update                      Update site to other version of OMD
# omd start      [SERVICE]        Start services of one or all sites
# omd stop       [SERVICE]        Stop services of site(s)
# omd restart    [SERVICE]        Restart services of site(s)
# omd reload     [SERVICE]        Reload services of site(s)
# omd status     [SERVICE]        Show status of services of site(s)
# omd config     ...              Show and set site configuration parameters
# omd diff       ([RELBASE])      Shows differences compared to the original version files
# omd umount                      Umount ramdisk volumes of site(s)
# omd backup     [SITE] [-|ARCHIVE_PATH] Create a backup tarball of a site, writing it to a file or stdout
# omd restore    [SITE] [-|ARCHIVE_PATH] Restores the backup of a site to an existing site or creates a new site
#
# General Options:
# -V <version>                    set specific version, useful in combination with update/create
# omd COMMAND -h, --help          show available options of COMMAND
