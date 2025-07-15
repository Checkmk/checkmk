#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
from collections.abc import Iterator

import pytest

from tests.scripts.opentelemetry_grpc import GRPC_METRIC_NAME, GRPC_PORT
from tests.scripts.opentelemetry_http import HTTP_METRIC_NAME, HTTP_PORT, PASSWORD, USERNAME
from tests.scripts.opentelemetry_prometheus import EXPECTED_PROMETHEUS_SERVICE_COUNT
from tests.testlib.opentelemetry import (
    delete_opentelemetry_data,
    opentelemetry_app,
    ScriptFileName,
    wait_for_opentelemetry_data,
)
from tests.testlib.site import Site

pytestmark = pytest.mark.skip_if_not_edition("cloud", "managed")

logger = logging.getLogger(__name__)

GRPC_CONFIG = {
    "endpoint": {
        "address": "0.0.0.0",
        "auth": {"type": "none"},
        "export_to_syslog": False,
        "host_name_rules": [
            [
                {"type": "free", "value": "cmk_"},
                {"type": "key", "value": "cmk.test.attribute1"},
            ],
            [{"type": "key", "value": "cmk.test.attribute2"}],
        ],
        "encryption": False,
        "port": GRPC_PORT,
    }
}

HTTP_CONFIG = {
    "endpoint": {
        "address": "127.0.0.1",
        "auth": {
            "type": "basicauth",
            "userlist": [
                {"username": USERNAME, "password": {"type": "explicit", "value": PASSWORD}}
            ],
        },
        "export_to_syslog": False,
        "host_name_rules": [
            [{"type": "key", "value": "cmk.test.attribute"}],
            [{"type": "free", "value": "fallback_host"}],
        ],
        "encryption": False,
        "port": HTTP_PORT,
    }
}


@pytest.fixture(scope="module")
def otel_site(site: Site) -> Iterator[Site]:
    """Fixture to enable OpenTelemetry collector on the site."""
    site.set_config("OPENTELEMETRY_COLLECTOR", "on", with_restart=True)
    yield site
    site.set_config("OPENTELEMETRY_COLLECTOR", "off", with_restart=True)


def delete_created_objects(
    site: Site, collector_id: str, host_name: str, rule_id: str | None
) -> None:
    if os.getenv("CLEANUP", "1") == "1":
        logger.info("Cleaning up created resources")
        site.openapi.otel_collector.delete(collector_id)
        site.openapi.hosts.delete(host_name)
        if rule_id:
            site.openapi.rules.delete(rule_id)
        site.openapi.changes.activate_and_wait_for_completion()
        delete_opentelemetry_data(site)


@pytest.mark.parametrize(
    "receiver_type, receiver_config, script_file_name, host_name, metric_name",
    [
        pytest.param(
            "grpc",
            GRPC_CONFIG,
            ScriptFileName.OTEL_GRPC,
            "cmk_otel_test",
            GRPC_METRIC_NAME,
            id="GRPC.Hostname_computation_uses_first_applicable_rule.",
        ),
        pytest.param(
            "http",
            HTTP_CONFIG,
            ScriptFileName.OTEL_HTTP,
            "fallback_host",
            HTTP_METRIC_NAME,
            id="HTTP.Basic_authentication.Fallback_host_name.",
        ),
    ],
)
def test_otel_collector_with_receiver_config(
    otel_site: Site,
    receiver_type: str,
    receiver_config: dict,
    script_file_name: ScriptFileName,
    host_name: str,
    metric_name: str,
) -> None:
    """Test that OpenTelemetry collector works as expected when configured using 'Receiver' option.

    This test creates an OpenTelemetry collector, a host with the name expected by the collector
    configuration and a rule for OpenTelemetry special agent. Then the script which generates
    OpenTelemetry data is started and after some time service discovery for the created host is
    triggered. Finally, it checks that the host received expected OpenTelemetry data.

    Args:
        otel_site: The site where the OpenTelemetry collector is enabled.
        receiver_type: Type of the receiver, either 'grpc' or 'http'.
        receiver_config: OpenTelemetry receiver configuration.
        script_file_name: The name of the script which generates OpenTelemetry data.
        host_name: The expected host name based on the configuration rules and the script.
        metric_name: The name of the metric expected to be created by the OpenTelemetry collector.
    """
    collector_id = "opentelemetry_collector"
    rule_id = None

    try:
        if receiver_type == "grpc":
            logger.info("Creating OpenTelemetry collector with GRPC receiver")
            otel_site.openapi.otel_collector.create(
                collector_id, "Test collector", False, receiver_protocol_grpc=receiver_config
            )
        elif receiver_type == "http":
            logger.info("Creating OpenTelemetry collector with HTTP receiver")
            otel_site.openapi.otel_collector.create(
                collector_id, "Test collector", False, receiver_protocol_http=receiver_config
            )
        else:
            raise ValueError(f"Unsupported receiver type: {receiver_type}")

        logger.info(
            "Creating a new host with the name expected from the otel host name computation"
        )
        otel_site.openapi.hosts.create(
            host_name,
            attributes={
                "tag_address_family": "no-ip",
                "tag_agent": "special-agents",
                "tag_piggyback": "no-piggyback",
            },
            folder="/",
        )

        logger.info("Adding a rule for OpenTelemetry special agent")
        rule_id = otel_site.openapi.rules.create(
            ruleset_name="special_agents:otel",
            value={"include_self_monitoring": False},
        )
        otel_site.openapi.changes.activate_and_wait_for_completion()

        with opentelemetry_app(script_file_name):
            wait_for_opentelemetry_data(otel_site, host_name)

            logger.info("Running service discovery and activating changes")
            otel_site.openapi.service_discovery.run_discovery_and_wait_for_completion(host_name)
            otel_site.openapi.changes.activate_and_wait_for_completion()

            logger.info("Checking OTel service is created and has expected state")
            services = otel_site.get_host_services(host_name)
            otel_service_name = f"OTel metric {metric_name}"
            assert otel_service_name in services, "OTel service was not found in host services"
            assert services[otel_service_name].state == 0, "OTel service is not in OK or PEND state"
    finally:
        delete_created_objects(otel_site, collector_id, host_name, rule_id)


def test_otel_collector_with_prometheus_scrape_config(otel_site: Site) -> None:
    """Test that OpenTelemetry collector works as expected when configured using 'Prometheus' option.

    This test creates a collector with a Prometheus scrape configuration that uses the
    'host name/IP address' for host name computation. It also creates a host with the name expected
    by the collector configuration and a rule for OpenTelemetry special agent. Then the script
    which creates a Prometheus server is started and after some time service discovery
    for the created host is triggered. Finally, it checks that the host received expected
    OpenTelemetry data.
    """
    collector_id = "opentelemetry_collector"
    prometheus_config = {
        "job_name": "test_job",
        "scrape_interval": 30,
        "metrics_path": "",
        "targets": [{"address": "localhost", "port": 9090}],
        "host_name_rules": [{"type": "service_instance_id"}],
        "encryption": False,
    }
    # This is the expected host name based on the rules defined in grpc_config
    host_name = "localhost"
    rule_id = None

    try:
        logger.info("Creating OpenTelemetry collector with Prometheus scrape configuration")
        otel_site.openapi.otel_collector.create(
            collector_id,
            "Test collector",
            False,
            prometheus_scrape_configs=[prometheus_config],
        )

        logger.info(
            "Creating a new host with the name expected from the otel host name computation"
        )
        otel_site.openapi.hosts.create(
            host_name,
            attributes={
                "tag_address_family": "no-ip",
                "tag_agent": "special-agents",
                "tag_piggyback": "no-piggyback",
            },
            folder="/",
        )

        logger.info("Adding a rule for OpenTelemetry special agent")
        rule_id = otel_site.openapi.rules.create(
            ruleset_name="special_agents:otel",
            value={"include_self_monitoring": False},
        )
        otel_site.openapi.changes.activate_and_wait_for_completion()

        with opentelemetry_app(ScriptFileName.PROMETHEUS):
            wait_for_opentelemetry_data(otel_site, host_name)

            logger.info("Running service discovery and activating changes")
            otel_site.openapi.service_discovery.run_discovery_and_wait_for_completion(host_name)
            otel_site.openapi.changes.activate_and_wait_for_completion()

            logger.info("Checking OTel services are created and have expected states")
            services = otel_site.get_host_services(host_name)
            assert len(services) == EXPECTED_PROMETHEUS_SERVICE_COUNT, (
                f"Unexpected number of services discovered: {services}"
            )
            for service_name, service in services.items():
                if service_name.startswith("OTel metric "):
                    assert service.state == 0, f"Service {service_name} is not in OK or PEND state"
    finally:
        delete_created_objects(otel_site, collector_id, host_name, rule_id)
