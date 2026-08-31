#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Activating a configuration change across a folder tree and a distributed setup."""

import itertools
import logging

from tests.performance.perftest import PerformanceTest

logger = logging.getLogger(__name__)


def setup_bulk_change_activation(perftest: PerformanceTest) -> None:
    """Setup: Bulk change activation

    Create location folders: "site-a", "site-b" and "site-c".
    In each location folder, create system folders: "windows", "linux" and "network".
    In each system folder, create environment folders: "dev", "qa" and "prod".
    In each environment folder, create 10 hosts, which inherit a host tag from each folder.
    """
    host_tag_groups = {
        "location": [
            {"id": "site-a", "title": "Site A"},
            {"id": "site-b", "title": "Site B"},
            {"id": "site-c", "title": "Site C"},
        ],
        "system": [
            {"id": "linux", "title": "Linux"},
            {"id": "windows", "title": "Windows"},
            {"id": "network", "title": "Network Device"},
        ],
        "environment": [
            {"id": "dev", "title": "Development"},
            {"id": "qa", "title": "QA"},
            {"id": "prod", "title": "Production"},
        ],
    }
    for host_tag_group_name, host_tag_group in host_tag_groups.items():
        perftest.central_site.openapi.host_tag_groups.create(
            name=host_tag_group_name,
            title=host_tag_group_name.capitalize(),
            tags=host_tag_group,
        )
    host_ip_offset = 0
    host_count = 10
    target_site_id_cycle = (
        itertools.cycle(perftest.bulk_change_target_site_ids)
        if perftest.bulk_change_target_site_ids
        else None
    )
    for location_id, location in enumerate(host_tag_groups["location"]):
        perftest.central_site.openapi.folders.create(
            folder=location["id"],
            title=location["title"],
            attributes={"tag_location": location["id"]},
        )
        for system in host_tag_groups["system"]:
            system_folder = f"/{location['id']}/{system['id']}"
            perftest.central_site.openapi.folders.create(
                folder=system_folder,
                title=system["title"],
                attributes={"tag_system": system["id"]},
            )
            for environment in host_tag_groups["environment"]:
                environment_folder = f"{system_folder}/{environment['id']}"
                perftest.central_site.openapi.folders.create(
                    folder=environment_folder,
                    title=environment["title"],
                    attributes={"tag_environment": environment["id"]},
                )
                perftest.central_site.openapi.hosts.bulk_create(
                    perftest.generate_hosts(
                        host_count,
                        perftest.central_site,
                        None if target_site_id_cycle else [perftest.sites[location_id]],
                        host_ip_offset,
                        folder=environment_folder,
                        target_site_ids=(
                            [next(target_site_id_cycle)] if target_site_id_cycle else None
                        ),
                    )
                )
                host_ip_offset += host_count


def teardown_bulk_change_activation(perftest: PerformanceTest) -> None:
    """Teardown: Bulk change activation"""
    for location_name in ("site-a", "site-b", "site-c"):
        perftest.central_site.openapi.folders.delete(folder=location_name, delete_mode="recursive")
    for tag_group_name in ("location", "system", "environment"):
        perftest.central_site.openapi.host_tag_groups.delete(name=tag_group_name)
    assert perftest.central_site.openapi.changes.activate_and_wait_for_completion()


def scenario_bulk_change_activation(perftest: PerformanceTest) -> None:
    """Scenario: Bulk change activation

    Setup: See setup_bulk_change_activation.
    Activate all pending changes and wait for completion.
    Teardown: See teardown_bulk_change_activation
    """
    perftest.central_site.ensure_running()
    assert perftest.central_site.openapi.changes.activate_and_wait_for_completion()
