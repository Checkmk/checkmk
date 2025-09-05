#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@contextmanager
def _with_different_content(site: Site, path: str, content: str) -> Iterator[None]:
    old_content = site.read_file(path, encoding=None)
    logging.info("Changing %s", path)
    try:
        site.write_file(path, content)
        yield
    finally:
        logging.info("Resetting %s to original state", path)
        site.write_file(path, old_content)


def _create_ping_host(site: Site, hostname: str) -> None:
    logging.info("Creating ping host %s", hostname)
    site.openapi.hosts.create(
        hostname=hostname,
        attributes={
            "tag_address_family": "ip-v4-only",
            "ipaddress": "127.0.0.1",
            "tag_agent": "no-agent",
        },
    )


def _wait_for_ping_rrd(site: Site, hostname: str) -> str:
    site.activate_changes_and_wait_for_core_reload(allow_foreign_changes=True)
    site.wait_until_service_has_been_checked(hostname, "PING")
    file_path = f"var/check_mk/rrd/{hostname}/PING.rrd"
    wait_until(
        lambda: site.file_exists(file_path),
        timeout=10,
        condition_name=f"RRD file for PING service of {hostname} creation",
    )
    return file_path


def _delete_host(site: Site, hostname: str) -> None:
    logging.info("Deleting ping host %s", hostname)
    site.openapi.hosts.delete(hostname)


@contextmanager
def _create_rrd_files(site: Site, hostname: str) -> Iterator[str]:
    _create_ping_host(site, hostname)
    try:
        yield _wait_for_ping_rrd(site, hostname)
    finally:
        _delete_host(site, hostname)


def test_diskspace_abandoned(site: Site) -> None:
    # Assemble
    keep_host = "test_keep_diskspace_host"
    delete_host = "test_delete_diskspace_host"

    # Create RRD file, which should be kept.
    with _create_rrd_files(site, keep_host) as keep_file_path:
        # Create RRD file, which doesn't belong to any host.
        _create_ping_host(site, delete_host)
        delete_file_path = _wait_for_ping_rrd(site, delete_host)
        _delete_host(site, delete_host)

        global_settings = """# Created by test_diskspace_abandoned
diskspace_cleanup = {'cleanup_abandoned_host_files': 0}
"""
        with _with_different_content(
            site, "etc/check_mk/diskspace.d/wato/global.mk", global_settings
        ):
            # Act
            site.run(["diskspace", "-v"]).check_returncode()
        # Assert
        assert not site.file_exists(delete_file_path)
        assert site.file_exists(keep_file_path)
