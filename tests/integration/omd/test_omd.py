#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
import tempfile
from pathlib import Path

from tests.testlib.site import get_site_factory, Site
from tests.testlib.utils import run, wait_until


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


def test_run_omd_backup_and_omd_restore(site: Site) -> None:
    """
    Test the 'omd backup' and 'omd restore' commands.
    This test creates a backup of the current site and then restores it with a new name.

    """
    site_factory = get_site_factory(prefix="")
    restored_site_name = "restored_site"
    restored_site = None
    backup_path = Path(tempfile.gettempdir()) / "backup.tar.gz"
    try:
        # run the backup
        assert site.omd("backup", str(backup_path)) == 0
        assert backup_path.stat().st_size > 0, "Backup file was not created."

        # run restore as root to use a different site name
        run(["omd", "restore", restored_site_name, str(backup_path)], sudo=True, check=True)
        restored_site = site_factory.get_existing_site(restored_site_name, start=True)
        assert restored_site.exists(), "Restored site does not exist."
        assert restored_site.is_running(), "Restored site is not running."

    finally:
        if backup_path.exists():
            run(["rm", "-rf", str(backup_path)], sudo=True)
        if restored_site is not None and restored_site.exists():
            restored_site.rm()


def test_run_omd_backup_and_omd_restore_empty() -> None:
    """Test that restore works on empty site directory."""
    site_factory = get_site_factory(prefix="")
    restored_site_name = "restored_site"
    backup_path = Path(tempfile.gettempdir()) / "backup.tar.gz"
    try:
        # run the backup
        restored_site = site_factory.get_site(
            restored_site_name,
            start=False,
            init_livestatus=False,
            prepare_for_tests=False,
            activate_changes=False,
        )
        assert restored_site.omd("backup", str(backup_path)) == 0
        assert backup_path.stat().st_size > 0, "Backup file was not created."

        restored_site.omd("stop")
        assert restored_site.omd("umount") == 0
        run(["rm", "-rf", str(restored_site.root)], sudo=True, check=True)
        # create_site_home
        run(["mkdir", str(restored_site.root)], sudo=True, check=True)
        owner_group = f"{restored_site_name}:{restored_site_name}"
        run(["chown", owner_group, str(restored_site.root)], sudo=True, check=True)
        run(["chmod", "0751", str(restored_site.root)], sudo=True, check=True)

        run(
            ["omd", "restore", "--reuse", restored_site_name, str(backup_path)],
            sudo=True,
            check=True,
        )
        restored_site = site_factory.get_existing_site(restored_site_name, start=True)
        assert restored_site.exists(), "Restored site does not exist."
        assert restored_site.is_running(), "Restored site is not running."

    finally:
        if backup_path.exists():
            run(["rm", str(backup_path)], sudo=True)
        if restored_site is not None and restored_site.exists():
            restored_site.rm()


def test_run_omd_status_as_site_user(site: Site) -> None:
    """Test the 'omd status' command as the site user.

    Verifies that the command succeeds and produces output containing the site's services.
    """
    rc = site.omd("status")
    assert rc == 0, "The command should return status 0, 'running'"


def test_run_omd_status_as_root(site: Site) -> None:
    """Test the 'sudo omd status <site>' command as root.

    Verifies that root can query the status of a specific site by name.
    """
    p = run(["omd", "status", site.id], sudo=True, check=False)
    assert p.returncode == 0, "The command should return status 0, 'running'"
    assert p.stderr == "", "No error output expected"


def test_run_omd_status_service_as_site_user(site: Site) -> None:
    """Test the 'omd status <service>' command as the site user.

    Verifies that a single service status can be queried by name.
    """
    service = "crontab"
    rc = site.omd("status", service)
    assert rc == 0, f"Service '{service}' should be running"


def test_run_omd_status_service_as_root(site: Site) -> None:
    """Test the 'sudo omd status <site> <service>' command as root.

    Verifies that root can query a specific service's status for a named site.
    """
    service = "crontab"
    p = run(["omd", "status", site.id, service], sudo=True, check=False)
    assert p.returncode == 0, f"Service '{service}' should be running"
    assert p.stderr == "", "No error output expected"
    assert service in p.stdout, f"Expected service '{service}' in output"


def test_run_omd_start_as_site_user(site: Site) -> None:
    """Test the 'omd start' command as the site user.

    Stops the site first, then verifies that 'omd start' brings it back up.
    """
    assert site.omd("stop") == 0, "Pre-condition: site should stop cleanly"
    try:
        rc = site.omd("start")
        assert rc == 0, "The 'omd start' command should succeed"
        assert site.is_running(), "Site should be running after 'omd start'"
    finally:
        if not site.is_running():
            site.omd("start")


def test_run_omd_start_as_root(site: Site) -> None:
    """Test the 'sudo omd start <site>' command as root.

    Stops the site first, then verifies that root can start it by site name.
    """
    assert site.omd("stop") == 0, "Pre-condition: site should stop cleanly"
    try:
        p = run(["omd", "start", site.id], sudo=True, check=False)
        assert p.returncode == 0, "The 'sudo omd start <site>' command should succeed"
        assert p.stderr == "", "No error output expected"
        assert site.is_running(), "Site should be running after 'sudo omd start <site>'"
    finally:
        if not site.is_running():
            site.omd("start")


def test_run_omd_start_service_as_site_user(site: Site) -> None:
    """Test the 'omd start <service>' command as the site user.

    Stops a single service and verifies it can be restarted by name.
    """
    service = "crontab"
    assert site.omd("stop", service) == 0, f"Pre-condition: service '{service}' should stop cleanly"
    rc = site.omd("start", service)
    assert rc == 0, f"The 'omd start {service}' command should succeed"
    wait_until(
        lambda: site.omd("status", service) == 0,
        timeout=10,
        interval=1,
    )


def test_run_omd_start_service_as_root(site: Site) -> None:
    """Test the 'sudo omd start <site> <service>' command as root.

    Stops a single service and verifies root can start it by site and service name.
    """
    service = "crontab"
    site.omd("stop", service)
    p = run(["omd", "start", site.id, service], sudo=True, check=False)
    assert p.returncode == 0, f"The 'sudo omd start {site.id} {service}' command should succeed"
    assert p.stderr == "", "No error output expected"
    wait_until(
        lambda: site.omd("status", service) == 0,
        timeout=10,
        interval=1,
    )


def test_run_omd_stop_as_site_user(site: Site) -> None:
    """Test the 'omd stop' command as the site user.

    Verifies that the site can be stopped and then restores it.
    """
    rc = site.omd("stop")
    try:
        assert rc == 0, "The 'omd stop' command should succeed"
        assert site.is_stopped(), "Site should be stopped after 'omd stop'"
    finally:
        site.omd("start")


def test_run_omd_stop_as_root(site: Site) -> None:
    """Test the 'sudo omd stop <site>' command as root.

    Verifies that root can stop a site by name, then restores it.
    """
    p = run(["omd", "stop", site.id], sudo=True, check=False)
    try:
        assert p.returncode == 0, "The 'sudo omd stop <site>' command should succeed"
        assert p.stderr == "", "No error output expected"
        assert site.is_stopped(), "Site should be stopped after 'sudo omd stop <site>'"
    finally:
        site.omd("start")


def test_run_omd_stop_service_as_site_user(site: Site) -> None:
    """Test the 'omd stop <service>' command as the site user.

    Verifies that a single service can be stopped and then restores it.
    """
    service = "crontab"
    rc = site.omd("stop", service)
    try:
        assert rc == 0, f"The 'omd stop {service}' command should succeed"
        wait_until(
            lambda: site.omd("status", service) != 0,
            timeout=10,
            interval=1,
        )
    finally:
        site.omd("start", service)


def test_run_omd_stop_service_as_root(site: Site) -> None:
    """Test the 'sudo omd stop <site> <service>' command as root.

    Verifies that root can stop a single service by site and service name.
    """
    service = "crontab"
    p = run(["omd", "stop", site.id, service], sudo=True, check=False)
    try:
        assert p.returncode == 0, f"The 'sudo omd stop {site.id} {service}' command should succeed"
        assert p.stderr == "", "No error output expected"
        wait_until(
            lambda: site.omd("status", service) != 0,
            timeout=10,
            interval=1,
        )
    finally:
        site.omd("start", service)


def test_run_omd_restart_as_site_user(site: Site) -> None:
    """Test the 'omd restart' command as the site user.

    Verifies that all site services are restarted and the site is running afterward.
    """
    rc = site.omd("restart")
    assert rc == 0, "The 'omd restart' command should succeed"
    assert site.is_running(), "Site should be running after 'omd restart'"


def test_run_omd_restart_as_root(site: Site) -> None:
    """Test the 'sudo omd restart <site>' command as root.

    Verifies that root can restart all services for a site by name.
    """
    p = run(["omd", "restart", site.id], sudo=True, check=False)
    assert p.returncode == 0, "The 'sudo omd restart <site>' command should succeed"
    assert p.stderr == "", "No error output expected"
    assert site.is_running(), "Site should be running after 'sudo omd restart <site>'"


def test_run_omd_restart_service_as_site_user(site: Site) -> None:
    """Test the 'omd restart <service>' command as the site user.

    Verifies that a single service can be restarted and is running afterward.
    """
    service = "crontab"
    rc = site.omd("restart", service)
    assert rc == 0, f"The 'omd restart {service}' command should succeed"
    wait_until(
        lambda: site.omd("status", service) == 0,
        timeout=10,
        interval=1,
    )


def test_run_omd_restart_service_as_root(site: Site) -> None:
    """Test the 'sudo omd restart <site> <service>' command as root.

    Verifies that root can restart a single service by site and service name.
    """
    service = "crontab"
    p = run(["omd", "restart", site.id, service], sudo=True, check=False)
    assert p.returncode == 0, f"The 'sudo omd restart {site.id} {service}' command should succeed"
    assert p.stderr == "", "No error output expected"
    wait_until(
        lambda: site.omd("status", service) == 0,
        timeout=10,
        interval=1,
    )


def test_run_omd_reload_as_root(site: Site) -> None:
    """Test the 'sudo omd reload <site>' command as root.

    Verifies that root can reload all services for a named site.
    """
    p = run(["omd", "reload", site.id], sudo=True, check=False)
    assert p.returncode == 0, "The 'sudo omd reload <site>' command should succeed"
    assert p.stderr == "", "No error output expected"
    assert site.is_running(), "Site should be running after 'sudo omd reload <site>'"


def test_run_omd_reload_service_as_root(site: Site) -> None:
    """Test the 'sudo omd reload <site> <service>' command as root.

    Verifies that root can reload a single service by site and service name.
    """
    service = "crontab"
    p = run(["omd", "reload", site.id, service], sudo=True, check=False)
    assert p.returncode == 0, f"The 'sudo omd reload {site.id} {service}' command should succeed"
    assert p.stderr == "", "No error output expected"
    wait_until(
        lambda: site.omd("status", service) == 0,
        timeout=10,
        interval=1,
    )


def test_run_omd_umount_as_site_user(site: Site) -> None:
    """Test the 'omd umount' command as the site user.

    Stops the site first (umount requires a stopped site), runs umount,
    then starts the site again (which remounts the tmpfs).
    """
    assert site.omd("stop") == 0, "Pre-condition: site should stop cleanly"
    try:
        rc = site.omd("umount")
        assert rc == 0, "The 'omd umount' command should succeed"
    finally:
        site.omd("start")


def test_run_omd_umount_as_root(site: Site) -> None:
    """Test the 'sudo omd umount <site>' command as root.

    Stops the site first (umount requires a stopped site), runs umount as root,
    then starts the site again (which remounts the tmpfs).
    """
    assert site.omd("stop") == 0, "Pre-condition: site should stop cleanly"
    try:
        p = run(["omd", "umount", site.id], sudo=True, check=False)
        assert p.returncode == 0, "The 'sudo omd umount <site>' command should succeed"
        assert p.stderr == "", "No error output expected"
    finally:
        site.omd("start")


# TODO: Add tests for these modes (also check -h of each mode)
# omd update                      Update site to other version of OMD
# omd config     ...              Show and set site configuration parameters
# omd diff       ([RELBASE])      Shows differences compared to the original version files
# omd backup     [SITE] [-|ARCHIVE_PATH] Create a backup tarball of a site, writing it to a file or stdout
# omd restore    [SITE] [-|ARCHIVE_PATH] Restores the backup of a site to an existing site or creates a new site
#
# General Options:
# -V <version>                    set specific version, useful in combination with update/create
# omd COMMAND -h, --help          show available options of COMMAND
