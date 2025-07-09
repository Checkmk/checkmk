#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
This module provides a collection of utility functions and context managers
for faking Checkmk agent hosts.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from tests.testlib.agent_dumps import (
    copy_dumps,
    dummy_agent_dump_generator,
    read_disk_dump,
    read_piggyback_hosts_from_dump,
)
from tests.testlib.common.repo import qa_test_data_path
from tests.testlib.dcd import dcd_connector, execute_dcd_cycle
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@contextmanager
def _fake_host_and_discover_services(
    site: Site,
    host_name: str,
    folder_name: str = "/",
    cleanup: bool = True,
) -> Iterator[None]:
    try:
        logger.info('Creating source host "%s"...', host_name)
        host_attributes = {"ipaddress": "127.0.0.1", "tag_agent": "cmk-agent"}
        site.openapi.hosts.create(
            hostname=host_name, folder=folder_name, attributes=host_attributes
        )
        site.openapi.changes.activate_and_wait_for_completion(
            force_foreign_changes=True, strict=False
        )

        logger.info("Running service discovery...")
        site.openapi.service_discovery.run_discovery_and_wait_for_completion(host_name)

        yield
    finally:
        if not cleanup:
            return

        logger.info('Deleting source host "%s"...', host_name)
        site.openapi.hosts.delete(host_name)
        site.openapi.changes.activate_and_wait_for_completion(
            force_foreign_changes=True, strict=False
        )


@contextmanager
def _discover_services_of_piggybacked_hosts(
    site: Site,
    host_name: str,
    expected_pb_hosts: list[str],
    folder_name: str = "/",
    cleanup: bool = True,
) -> Iterator[None]:
    with _fake_host_and_discover_services(site, host_name, folder_name, cleanup):
        execute_dcd_cycle(site, expected_pb_hosts=len(expected_pb_hosts))

        if expected_pb_hosts:
            existing_pb_hosts = site.openapi.hosts.get_all_names(allow=expected_pb_hosts)
            missing_pb_hosts = [_ for _ in expected_pb_hosts if _ not in existing_pb_hosts]
            assert existing_pb_hosts, f'No piggybacked hosts found for source host "{host_name}"'
            assert not missing_pb_hosts, (
                f'Piggybacked hosts missing from source host "{host_name}: {missing_pb_hosts}'
            )
            for piggybacked_host_name in expected_pb_hosts + [host_name]:
                site.reschedule_services(piggybacked_host_name, 3, strict=False)

        yield


@contextmanager
def piggyback_host_from_dump_file(
    site: Site,
    dump_name: str,
    folder_name: str = "/",
    dcd_interval: int = 5,
    source_dir: Path = Path("plugins_integration/dumps/piggyback"),
    target_dir: Path = Path("var/check_mk/dumps"),
    cleanup: bool = True,
) -> Iterator[None]:
    """Create a piggyback host from a dump file.

    Args:
        site: The test site.
        dump_name: The name of the dump file, which will also be the host name.
        folder_name: The name of the host folder in the site which the host is created in.
        dcd_interval: The dcd interval in seconds.
        source_dir: The source dir of the dump file.
        target_dir: The target dir of the dump file.
        cleanup: Specifies if the dump file is cleaned up at the end.
    """
    source_dir = source_dir if source_dir.is_absolute() else (qa_test_data_path() / source_dir)
    target_dir = target_dir if target_dir.is_absolute() else site.path(target_dir)
    piggybacked_hosts = list(read_piggyback_hosts_from_dump(read_disk_dump(dump_name, source_dir)))
    try:
        copy_dumps(site, source_dir, target_dir, source_filename=dump_name)
        with dcd_connector(site, interval=dcd_interval, cleanup=cleanup):
            with _discover_services_of_piggybacked_hosts(
                site, dump_name, piggybacked_hosts, folder_name, cleanup
            ):
                yield
    finally:
        if cleanup:
            site.run(["rm", "-f", f"{target_dir}/{dump_name}"])


@contextmanager
def piggyback_host_from_dummy_generator(
    site: Site,
    host_name: str,
    folder_name: str = "/",
    dcd_interval: int = 5,
    pb_host_count: int = 10,
    pb_service_count: int = 10,
    cleanup: bool = True,
) -> Iterator[tuple[str, list[str]]]:
    """Create a piggyback host using a dummy generator.

    Args:
        site: The test site.
        host_name: The name of the host to be created.
        folder_name: The name of the host folder in the site which the host is created in.
        dcd_interval: The dcd interval in seconds.
        cleanup: Specifies if the dump file is cleaned up at the end.
    """
    piggybacked_hosts = [f"{host_name}-pb-{_}" for _ in range(1, pb_host_count + 1)]
    with dcd_connector(
        site,
        interval=dcd_interval,
        no_deletion_time_after_init=60,
        max_cache_age=60,
        validity_period=60,
        cleanup=cleanup,
    ):
        with dummy_agent_dump_generator(
            site,
            service_count=0,
            payload_lines=0,
            pb_host_count=pb_host_count,
            pb_service_count=pb_service_count,
            rule_folder=folder_name,
        ) as rule_id:
            with _discover_services_of_piggybacked_hosts(
                site, host_name, piggybacked_hosts, folder_name, cleanup
            ):
                yield rule_id, piggybacked_hosts
