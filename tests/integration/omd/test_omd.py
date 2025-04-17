#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import tempfile
from pathlib import Path

import pytest

from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import run
from tests.testlib.version import version_from_env

_logger = logging.getLogger(__name__)


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
    assert len(service_state) == 2, (
        "The line is expected to have two parts in following format:"
        "\n<servicename> <status-integer-code>"
    )

    assert service_state[0] == "OVERALL", "The last line should be the overall status"
    try:
        assert int(service_state[1]) in (0, 1, 2), "The status should be one of 0, 1, 2"
    except ValueError as excp:
        # ValueError will be raised if service_state[1] can not
        # be parsed as an integer.
        excp.add_note("Expected status of service to be an integer!")
        raise excp


@pytest.mark.parametrize(
    "cmd_option, bake_agents, patterns_not_allowed",
    [
        (
            None,
            False,
            [],
        ),
        (
            "--no-past",
            False,
            [
                "var/check_mk/core/history",
            ],
        ),
        (
            "--no-agents",
            True,
            [
                "var/check_mk/agents*/*",
            ],
        ),
    ],
)
def test_run_omd_backup_and_omd_restore(
    site: Site, cmd_option: str, bake_agents: bool, patterns_not_allowed: list
) -> None:
    """
    Test the 'omd backup' and 'omd restore' commands.
        * without special options
        * with options --no-past and --no-agents

    This test creates a backup of the current site and then restores it with a new name.

    Args:
        cmd_option: command line option for "omd backup"
        bake_agents: Should we bake agents on the site to be backed up?
        patterns_not_allowed: list of globular patterns to check for disallowed files
    """
    site_factory = SiteFactory(
        version=version_from_env(),
        enforce_english_gui=False,
        prefix="",
    )

    # TODO: run from a new site for "--no-past" and "--no-agents"

    if bake_agents:
        logging.info("Baking agents for site '%s'", site.id)
        site.run(["cmk", "--bake-agents"])

    # test sanity check: check that the files exist only after startup and site preparation
    # (they are allowed and should exist NOW, but NOT in the backup)
    # -> this way we will notice, if the application implementation using these files changed
    #    (test might need to be adapted then)
    for pattern in patterns_not_allowed:
        files_existing_in_site = site.run(
            ["find", str(site.root), "-path", f"{site.root}/{pattern}"]
        ).stdout.splitlines()
        assert files_existing_in_site, f"Files '{pattern}' should exist in started/running site."
        logging.info(
            "OK: Found %d files matching '%s' in running/prepared backup site '%s'",
            len(files_existing_in_site),
            pattern,
            site.id,
        )

    restored_site_name = "restored_site"
    restored_site = None
    backup_path = Path(tempfile.gettempdir()) / "backup.tar.gz"
    try:
        # run the backup
        if cmd_option is None:
            backup_cmd = ["omd", "backup", site.id, str(backup_path)]
        else:
            backup_cmd = ["omd", "backup", cmd_option, site.id, str(backup_path)]
        logging.info("Running backup with '%s'", " ".join(backup_cmd))
        run(backup_cmd, sudo=True, check=True)
        assert backup_path.stat().st_size > 0, "Backup file was not created."

        # run restore
        # (don't start yet, as we want to check the files first)
        run(["omd", "restore", restored_site_name, str(backup_path)], sudo=True, check=True)
        restored_site = site_factory.get_existing_site(restored_site_name, start=False)
        assert restored_site.exists(), "Restored site does not exist."
        assert not restored_site.is_running(), "Restored site should not be auto-started."

        # check that forbidden files are not in the restored site
        # (depending on the backup option)
        forbidden_files = []
        for pattern in patterns_not_allowed:
            files_existing_in_site = restored_site.run(
                ["find", str(restored_site.root), "-path", f"{restored_site.root}/{pattern}"]
            ).stdout.splitlines()
            if files_existing_in_site:
                logging.info(
                    "Detected %d forbidden files in the backup for '%s': %s",
                    len(files_existing_in_site),
                    pattern,
                    files_existing_in_site,
                )
                forbidden_files.extend(files_existing_in_site)
        if forbidden_files:
            raise AssertionError(
                f"Detected {len(forbidden_files)} forbidden files in the backup: {forbidden_files}."
            )

        # now start the restored site
        restored_site.start()
        assert restored_site.is_running(), "Restored site is not running."

    finally:
        if backup_path.exists():
            run(["rm", "-rf", str(backup_path)], sudo=True)
        if restored_site is not None and restored_site.exists():
            restored_site.rm()


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
#
# General Options:
# -V <version>                    set specific version, useful in combination with update/create
# omd COMMAND -h, --help          show available options of COMMAND
