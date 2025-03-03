#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.site import Site


def test_run_omd(site: Site) -> None:
    p = site.run(["omd"], check=False)
    assert p.returncode == 1
    assert p.stderr == ""
    assert "Usage" in p.stdout
    assert "omd COMMAND -h" in p.stdout


def test_run_omd_help(site: Site) -> None:
    p = site.run(["omd", "help"])
    assert p.stderr == ""
    assert "Usage" in p.stdout
    assert "omd COMMAND -h" in p.stdout


def test_run_omd_version(site: Site) -> None:
    p = site.run(["omd", "version"])
    assert p.stderr == ""
    assert p.stdout.endswith("%s\n" % site.version.omd_version())


def test_run_omd_version_bare(site: Site) -> None:
    p = site.run(["omd", "version", "-b"])
    assert p.stderr == ""
    assert p.stdout.rstrip("\n") == site.version.omd_version()


def test_run_omd_versions(site: Site) -> None:
    p = site.run(["omd", "versions"])
    assert p.stderr == ""
    versions = [v.split(" ", 1)[0] for v in p.stdout.split("\n")]
    assert len(versions) >= 1
    assert site.version.omd_version() in versions


def test_run_omd_versions_bare(site: Site) -> None:
    p = site.run(["omd", "versions", "-b"])
    assert p.stderr == ""
    versions = p.stdout.split("\n")
    assert len(versions) >= 1
    assert site.version.omd_version() in versions


def test_run_omd_sites(site: Site) -> None:
    p = site.run(["omd", "sites"])
    assert p.stderr == ""
    assert site.id in p.stdout


def test_run_omd_sites_bare(site: Site) -> None:
    p = site.run(["omd", "sites", "-b"])
    assert p.stderr == ""
    sites = p.stdout.split("\n")
    assert len(sites) >= 1
    assert site.id in sites


def test_run_omd_status_bare(site: Site) -> None:
    """
    Test the 'omd status --bare' command for the current site.
    Verifies that each line in the output follows the expected format,
    which is a service name followed by a number representing its status.
    """

    p = site.run(
        ["omd", "-v", "status", "--bare"],
        text=True,
        check=False,
    )
    assert p.returncode == 0, "The command should return status 0, 'running'"
    assert p.stderr == "", "No error output expected"
    services = p.stdout.splitlines()
    assert len(services) > 1, "Expected at least one line of service status"
    # check format of single line (e.g. "jaeger 5")
    # (used in AutomationGetRemoteOMDStatus()._parse_omd_status)
    service_state = services[-1].split(" ")
    assert len(service_state) == 2, "The line is expected to have two parts separated by a space"

    assert service_state[0] == "OVERALL", "The last line should be the overall status"
    try:
        assert int(service_state[1]) in (0, 1, 2), "The status should be one of 0, 1, 2"
    except ValueError as excp:
        # ValueError will be raised if service_state[1] can not
        # be parsed as an integer.
        excp.add_note("Expected status of service to be an integer!")
        raise excp


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
