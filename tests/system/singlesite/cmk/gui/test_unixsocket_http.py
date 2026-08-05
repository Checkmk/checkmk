#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from tests.testlib.site import Site


def test_automation_helper_and_ui_job_scheduler_unaffected_by_proxies(site: Site) -> None:
    """
    Test that the automation helper and UI job scheduler work correctly even when a proxy is set
    in the site profile. Deleting a host triggers an automation call, activating changes involves
    the UI job scheduler.
    """
    hostname = "aut-helper-test-host"
    try:
        with site.backup_and_restore_files([Path(".profile")]):
            site.write_file(
                ".profile",
                site.read_file(".profile") + "\nexport HTTP_PROXY=http://proxy.example.com:8080\n",
            )
            site.omd("restart", "apache", check=True)
            site.openapi.hosts.create(
                hostname,
                attributes={"ipaddress": "127.0.0.1"},
            )
            site.openapi.hosts.delete(hostname)
            site.openapi.changes.activate_and_wait_for_completion()
    finally:
        site.omd("restart", "apache", check=True)
        if hostname in site.openapi.hosts.get_all_names():
            site.openapi.hosts.delete(hostname)
            site.openapi.changes.activate_and_wait_for_completion()
