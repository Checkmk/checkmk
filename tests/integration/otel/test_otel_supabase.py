#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.testlib.common.repo import qa_test_data_path, repo_path
from tests.testlib.site import Site
from tests.testlib.utils import run

logger = logging.getLogger(__name__)


@pytest.fixture()
def inject_supabase_data(otel_site: Site) -> Iterator[None]:
    """Inject supabase OpenTelemetry data into the site, create a rule to process it and
    create a corresponding host. Delete all the created objects at the end of the test.
    """
    python_script_name = "generate_windows_and_linux_dumps.py"
    python_script_path = repo_path() / "tests/scripts" / python_script_name
    supabase_dump_file = qa_test_data_path() / "otel" / "supabase"
    test_site_dump_path = otel_site.path(Path("var/check_mk/dumps"))

    logger.info("Create a folder '%s' for dumps inside test site", test_site_dump_path)
    if not otel_site.is_dir(test_site_dump_path):
        otel_site.makedirs(test_site_dump_path)

    logger.info("Copying supabase data into the site directory")
    assert (
        run(["cp", str(supabase_dump_file), str(test_site_dump_path)], sudo=True).returncode == 0
    ), f"Error copying '{supabase_dump_file}' file"
    assert (
        run(
            ["cp", "-f", str(python_script_path), str(test_site_dump_path)],
            sudo=True,
        ).returncode
        == 0
    ), f"Error copying '{python_script_path}' file"

    ruleset_name = "datasource_programs"
    rule_value = f"python3 {test_site_dump_path}/{python_script_name} {test_site_dump_path}/<HOST>"
    logger.info(f"Creating rule '{ruleset_name}' with value: '{rule_value}'")
    rule_id = otel_site.openapi.rules.create(
        value=rule_value,
        ruleset_name=ruleset_name,
        folder="/",
    )
    host_name = "supabase"
    logger.info(f"Creating host '{host_name}' to receive the supabase data")
    otel_site.openapi.hosts.create(
        hostname=host_name,
        folder="/",
        attributes={
            "ipaddress": "127.0.0.1",
            "tag_agent": "cmk-agent",
        },
    )
    otel_site.openapi.changes.activate_and_wait_for_completion()

    yield
    if os.getenv("CLEANUP", "1") == "1":
        logger.info("Cleaning up created objects")
        otel_site.openapi.rules.delete(rule_id)
        otel_site.openapi.hosts.delete(host_name)
        otel_site.openapi.changes.activate_and_wait_for_completion()
        otel_site.delete_dir(test_site_dump_path)


EXPECTED_SERVICES_DATA = {
    "connection_stats_connection_count": {
        "summary": "Number of active connections",
        "performance_data": {
            "sb_dest_cluster_true__server_localhost_5432__service_type_postgresql__supabase_identifier_agvliauvhitpqjvajhxu__supabase_project_ref_agvliauvhitpqjvajhxu__username_supabase_admin": 5,
            "sb_dest_cluster_true__server_localhost_5432__service_type_postgresql__supabase_identifier_agvliauvhitpqjvajhxu__supabase_project_ref_agvliauvhitpqjvajhxu__username_postgres": 11,
            "sb_dest_cluster_true__server_localhost_5432__service_type_postgresql__supabase_identifier_agvliauvhitpqjvajhxu__supabase_project_ref_agvliauvhitpqjvajhxu__username_other": 6,
            "sb_dest_cluster_true__server_localhost_5432__service_type_postgresql__supabase_identifier_agvliauvhitpqjvajhxu__supabase_project_ref_agvliauvhitpqjvajhxu__username_authenticator": 1,
        },
    },
    "db_sql_connection_closed_max_idle_time_total": {
        "summary": "The total number of connections closed due to SetConnMaxIdleTime",
        "performance_data": {
            "sb_dest_cluster_true__service_type_gotrue__supabase_identifier_agvliauvhitpqjvajhxu__supabase_project_ref_agvliauvhitpqjvajhxu__per_sec": 0
        },
    },
    "db_sql_connection_max_open": {
        "summary": "Maximum number of open connections to the database",
        "performance_data": {
            "sb_dest_cluster_true__service_type_gotrue__supabase_identifier_agvliauvhitpqjvajhxu__supabase_project_ref_agvliauvhitpqjvajhxu": 10
        },
    },
    "go_memstats_alloc_bytes": {
        "summary": "Number of bytes allocated and still in use.",
        "performance_data": {
            "sb_dest_cluster_true__service_type_gotrue__supabase_identifier_agvliauvhitpqjvajhxu__supabase_project_ref_agvliauvhitpqjvajhxu": 1950080.0,
            "sb_dest_cluster_true__service_type_postgresql__supabase_identifier_agvliauvhitpqjvajhxu__supabase_project_ref_agvliauvhitpqjvajhxu": 2423650.0,
        },
    },
    "node_disk_filesystem_info": {
        "summary": "Info about disk filesystem.",
        "performance_data": {
            "device_nvme0n1__sb_dest_cluster_true__service_type_db__supabase_identifier_agvliauvhitpqjvajhxu__supabase_project_ref_agvliauvhitpqjvajhxu__type_ext4__usage_filesystem__uuid_92086b8b_0712_42a4_8036_46141ee38efb__version_1_0": 1
        },
    },
    "node_memory_SwapTotal_bytes": {
        "summary": "Memory information field SwapTotal_bytes.",
        "performance_data": {
            "sb_dest_cluster_true__service_type_db__supabase_identifier_agvliauvhitpqjvajhxu__supabase_project_ref_agvliauvhitpqjvajhxu": 1073740000.0
        },
    },
    "pgbouncer_databases_disabled": {
        "summary": "1 if this database is currently disabled, else 0",
        "performance_data": {
            "database_postgres__host_localhost__name_postgres__port_5432__sb_dest_cluster_true__service_type_db__supabase_identifier_agvliauvhitpqjvajhxu__supabase_project_ref_agvliauvhitpqjvajhxu": 0,
            "database_pgbouncer__force_user_pgbouncer__name_pgbouncer__pool_mode_statement__port_6543__sb_dest_cluster_true__service_type_db__supabase_identifier_agvliauvhitpqjvajhxu__supabase_project_ref_agvliauvhitpqjvajhxu": 0,
        },
    },
    "pg_stat_database_most_recent_reset": {
        "summary": "The most recent time one of the databases had its statistics reset, sb_dest_cluster_true__server_localhost_5432__service_type_postgresql__supabase_identifier_agvliauvhitpqjvajhxu__supabase_project_ref_agvliauvhitpqjvajhxu contains the value NaN(?)",
        "performance_data": {},
    },
    "physical_replication_lag_is_wal_replay_paused": {
        "summary": "Check if WAL replay has been paused",
        "performance_data": {
            "sb_dest_cluster_true__server_localhost_5432__service_type_postgresql__supabase_identifier_agvliauvhitpqjvajhxu__supabase_project_ref_agvliauvhitpqjvajhxu": 0
        },
    },
    "process_virtual_memory_bytes": {
        "summary": "Virtual memory size in bytes.",
        "performance_data": {
            "sb_dest_cluster_true__service_type_gotrue__supabase_identifier_agvliauvhitpqjvajhxu__supabase_project_ref_agvliauvhitpqjvajhxu": 1283940000.0,
            "sb_dest_cluster_true__service_type_postgresql__supabase_identifier_agvliauvhitpqjvajhxu__supabase_project_ref_agvliauvhitpqjvajhxu": 1266980000.0,
        },
    },
    "node_vmstat_pgpgin": {
        "summary": "/proc/vmstat information field pgpgin.",
        "performance_data": {
            "sb_dest_cluster_true__service_type_db__supabase_identifier_agvliauvhitpqjvajhxu__supabase_project_ref_agvliauvhitpqjvajhxu": 16194500.0
        },
    },
    "scrape_duration_seconds": {
        "summary": "0.25 s",
        "performance_data": {"scrape_duration_seconds__s": 0.253789},
    },
    "scrape_samples_scraped": {
        "summary": "489.00",
        "performance_data": {"scrape_samples_scraped": 489},
    },
    "up": {
        "summary": "1.00",
        "performance_data": {"up": 1},
    },
}

SERVICES_IN_UNKNOWN_STATE = [
    "OTel metric replication_slots_max_lag_bytes",
    "OTel metric pg_stat_replication_send_lag",
    "OTel metric pg_stat_replication_replay_lag",
    "OTel metric pg_stat_database_most_recent_reset",
]


@pytest.mark.skip_if_not_edition("cloud", "managed")
def test_otel_supabase(otel_site: Site, inject_supabase_data: None) -> None:
    """Test OpenTelemetry monitoring of a Supabase instance.

    The test injects OpenTelemetry data from a Supabase instance into the test site and simulates
    agent's behavior with a python script which returns this dumped data.
    The test checks that all the expected services are created, have correct states, and for some
    services, verifies the summaries and performance data.
    """
    host_name = "supabase"
    expected_services_count = 280
    expected_services_in_pend_state_count = 3

    logger.info("Running service discovery and activating changes for the host %s", host_name)
    otel_site.openapi.service_discovery.run_discovery_and_wait_for_completion(host_name)
    otel_site.openapi.changes.activate_and_wait_for_completion()
    for i in range(3):
        otel_site.schedule_check(host_name, "Check_MK", 0)

    logger.info(f"Retrieving services for host {host_name}")
    services = otel_site.get_host_services(
        host_name, extra_columns=["has_been_checked", "performance_data"]
    )

    logger.info("Checking that the expected number of services are present")
    assert (
        len(services) == expected_services_count
    ), f"Expected {expected_services_count} services, but found {len(services)}"
    active_services = {
        name: data for name, data in services.items() if data.extra_columns["has_been_checked"]
    }
    pend_services_amount = len(services) - len(active_services)
    assert pend_services_amount == expected_services_in_pend_state_count, (
        f"More than {expected_services_in_pend_state_count} services are in Pending state, "
        f"({pend_services_amount} found)"
    )

    logger.info("Checking that all services have expected states")
    for service_name, service_data in active_services.items():
        try:
            assert service_data.state == 0, (
                f"Service '{service_name}' has unexpected state. "
                f"Expected: 0 (OK), actual: {service_data.state}"
            )
        except AssertionError as e:
            if service_name in SERVICES_IN_UNKNOWN_STATE:
                assert service_data.state == 3, (
                    f"Service '{service_name}' has unexpected state. "
                    f"Expected: 3 (UNKNOWN), actual: {service_data.state}"
                )
            else:
                raise e

    logger.info("Checking that some services have expected summaries and performance data")
    for metric_name, expected_result in EXPECTED_SERVICES_DATA.items():
        service = active_services.get(f"OTel metric {metric_name}")
        assert service is not None, f"Service for metric '{metric_name}' not found"
        assert service.summary == expected_result["summary"], (
            f"Service '{metric_name}' has unexpected summary. "
            f"Expected: {expected_result['summary']}, actual: {service.summary}"
        )
        assert service.extra_columns["performance_data"] == expected_result["performance_data"], (
            f"Service '{metric_name}' has unexpected performance data. "
            f"Expected: {expected_result['performance_data']}, "
            f"actual: {service.extra_columns['performance_data']}"
        )
