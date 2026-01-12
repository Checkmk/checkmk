#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.testlib.agent_dumps import copy_dumps, create_agent_dump_rule
from tests.testlib.common.repo import repo_path
from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site
from tests.testlib.utils import run

pytestmark = pytest.mark.skip_if_not_edition("cloud", "managed")

logger = logging.getLogger(__name__)

DUMP_SOURCE_DIR = repo_path() / "tests" / "integration" / "otel" / "data" / "otel_dumps"
SITE_DUMP_DIR = Path("var/check_mk/dumps")
RULESET_NAME = "checkgroup_parameters:otel_metrics"
DEFAULT_CMK_SERVICE_COUNT = 2  # Check_MK and Check_MK Discovery


@pytest.fixture(scope="module", autouse=True)
def inject_otel_dumps(otel_site: Site) -> Iterator[None]:
    """Inject dumps with OpenTelemetry data into the site, add a rule to process them and
    create corresponding hosts. Delete all the created objects at the end of the test module.
    """
    dump_rule_id, _ = create_agent_dump_rule(otel_site, otel_site.path(SITE_DUMP_DIR))
    copy_dumps(otel_site, DUMP_SOURCE_DIR, SITE_DUMP_DIR)
    # change ownership of the dumps folder to the site user to allow modification of the dumps
    run(
        ["chown", "-R", f"{otel_site.id}:{otel_site.id}", str(otel_site.path(SITE_DUMP_DIR))],
        sudo=True,
    )
    dump_names = os.listdir(DUMP_SOURCE_DIR)
    hosts = [
        {
            "host_name": dump_name,
            "folder": "/",
            "attributes": {
                "ipaddress": "127.0.0.1",
                "tag_agent": "cmk-agent",
            },
        }
        for dump_name in dump_names
    ]
    otel_site.openapi.hosts.bulk_create(entries=hosts)
    otel_site.openapi.changes.activate_and_wait_for_completion()
    yield
    # delete the folder
    otel_site.delete_dir(SITE_DUMP_DIR)
    # remove the rule
    otel_site.openapi.rules.delete(dump_rule_id)
    # delete the hosts
    otel_site.openapi.hosts.bulk_delete(dump_names)
    otel_site.openapi.changes.activate_and_wait_for_completion()


def update_dump(site: Site, dump_path: Path) -> None:
    """Update dump file to have a fresh timestamp in the last metric line."""
    lines = site.read_file(dump_path).strip().split("\n")
    timestamp, metric_values = lines[-1].split(" ", 1)
    new_timestamp = str(int(time.time()))
    # Replace all instances of the timestamp in metric_values with the new timestamp
    updated_metric_values = metric_values.replace(timestamp, new_timestamp)
    updated_metric_line = f"{new_timestamp} {updated_metric_values}"
    content = "\n".join(lines) + "\n" + updated_metric_line
    site.write_file(dump_path, content)


@pytest.mark.parametrize(
    "host_name, rule, expected_service_states, dump_update_required",
    [
        pytest.param(
            "agent-otel-fixed-levels",
            {
                "metrics": (
                    "all_metrics",
                    {
                        "rate_computation": "never",
                        "aggregation": "latest",
                        "levels_lower": ("fixed", (30.0, 15.0)),
                        "levels_upper": ("fixed", (50.0, 65.0)),
                    },
                )
            },
            {
                "random_value_gauge_1": 2,
                "random_value_gauge_2": 1,
                "random_value_gauge_3": 1,
                "random_value_gauge_4": 2,
            },
            False,
            id="otel_rule_fixed_levels",
        ),
        pytest.param(
            "agent-otel-aggregation",
            {
                "metrics": (
                    "all_metrics",
                    {
                        "rate_computation": "never",
                        "aggregation": "max",
                        "levels_lower": ("no_levels", None),
                        "levels_upper": ("fixed", (80.0, 90.0)),
                    },
                )
            },
            {
                "random_value_gauge": 2,
            },
            False,
            id="test_otel_rule_aggregation",
        ),
        pytest.param(
            "agent-otel-rate",
            {
                "metrics": (
                    "all_metrics",
                    {
                        "rate_computation": "always",
                        "aggregation": "latest",
                        "levels_lower": ("fixed", (1.0, 0.5)),
                        "levels_upper": ("no_levels", None),
                    },
                )
            },
            {
                "random_value_gauge": 2,
            },
            True,
            id="otel_rule_with_rate",
        ),
        pytest.param(
            "agent-otel-metric-filters",
            {
                "metrics": (
                    "multi_metrics",
                    [
                        {
                            "metric_name": "region_asia",
                            "aggregation": "latest",
                            "rate_computation": "never",
                            "levels_lower": ("no_levels", None),
                            "levels_upper": ("fixed", (100.0, 130.0)),
                        },
                        {
                            "metric_name": "observable_gauge_2",
                            "aggregation": "latest",
                            "rate_computation": "never",
                            "levels_lower": ("fixed", (30.0, 20.0)),
                            "levels_upper": ("no_levels", None),
                        },
                    ],
                )
            },
            {
                "observable_gauge_1": 1,
                "observable_gauge_2": 2,
                "observable_gauge_3": 0,
            },
            False,
            id="otel_rule_with_metric_filters",
        ),
    ],
)
def test_otel_service_monitoring_rules(
    otel_site: Site,
    host_name: str,
    rule: dict[str, object],
    expected_service_states: dict[str, int],
    dump_update_required: bool,
) -> None:
    """Test OpenTelemetry service monitoring rules with different configurations:

    otel_rule_fixed_levels: fixed lower and upper levels for all metrics;
    otel_rule_with_aggregation: aggregation using maximum for all metrics;
    otel_rule_with_rate: rate computation and fixed lower levels for all metrics;
    otel_rule_with_metric_filters: two metrics filters (one for the multiple datapoints metric,
    and one for a single datapoint metric) with fixed levels.
    """
    expected_services_count = DEFAULT_CMK_SERVICE_COUNT + len(expected_service_states)

    logger.info("Creating new OpenTelemetry service rule")
    rule_id = otel_site.openapi.rules.create(value=rule, ruleset_name=RULESET_NAME)

    try:
        logger.info("Running service discovery and activating changes for the host %s", host_name)
        otel_site.openapi.service_discovery.run_discovery_and_wait_for_completion(host_name)
        otel_site.openapi.changes.activate_and_wait_for_completion()

        if dump_update_required:
            otel_site.schedule_check(host_name, "Check_MK", 0, 5)
            update_dump(otel_site, SITE_DUMP_DIR / host_name)
            otel_site.schedule_check(host_name, "Check_MK", 0, 5)
        else:
            logger.info("Rescheduling services until no pending services are found")
            otel_site.reschedule_services(host_name, max_count=3)

        logger.info(f"Retrieving services for host {host_name}")
        services = otel_site.get_host_services(host_name, pending=False)
        assert (
            len(services) == expected_services_count
        ), f"Expected {expected_services_count} services, but found {len(services)}"

        logger.info("Checking that services are in the expected states")
        for metric_name, expected_state in expected_service_states.items():
            service_name = f"OTel metric {metric_name}"
            service = services.get(service_name)
            assert service is not None, f"Service for metric '{metric_name}' not found"
            # To prevent flakes, reschedule the service if it's not in the expected state yet
            wait_until(
                lambda: otel_site.is_service_in_expected_state_after_rescheduling(
                    host_name, service_name, expected_state
                ),
                timeout=30,
                interval=5,
            )

    finally:
        logger.info("Deleting the created OpenTelemetry rule")
        otel_site.openapi.rules.delete(rule_id)
        otel_site.openapi.changes.activate_and_wait_for_completion()
