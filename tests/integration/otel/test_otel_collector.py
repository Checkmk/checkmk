#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
import yaml

from cmk.ccc.hostaddress import HostName
from tests.testlib.agent import (
    agent_controller_daemon,
    download_and_install_agent_package,
    register_controller,
    uninstall_agent_package,
)
from tests.testlib.common.repo import repo_path
from tests.testlib.opentelemetry import otel_collector_enabled, wait_for_opentelemetry_data
from tests.testlib.site import Site
from tests.testlib.version import edition_from_env

try:
    from cmk.otel_collector.constants import (  # type: ignore[import-untyped, unused-ignore, import-not-found]
        SELF_MONITORING_FOLDER,
    )

    SELF_MONITORING_HOST = SELF_MONITORING_FOLDER
except ImportError:
    # cmk.otel_collector.constants is not available in non-Cloud/Managed editions
    # tests are only run in Cloud/Managed editions
    SELF_MONITORING_HOST = ""

# Apply the skipif marker to all tests in this file for non Managed or Cloud edition
pytestmark = [
    pytest.mark.skipif(
        not any([edition_from_env().is_cloud_edition(), edition_from_env().is_managed_edition()]),
        reason="otel-collector only shipped with Cloud or Managed",
    )
]

logger = logging.getLogger(__name__)


@pytest.fixture(name="installed_agent_ctl_in_unknown_state", scope="function")
def _installed_agent_ctl_in_unknown_state(
    site: Site, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    return download_and_install_agent_package(site, tmp_path_factory.mktemp("agent"))


@pytest.fixture(name="agent_ctl", scope="function")
def _agent_ctl(installed_agent_ctl_in_unknown_state: Path) -> Iterator[Path]:
    with agent_controller_daemon(installed_agent_ctl_in_unknown_state):
        yield installed_agent_ctl_in_unknown_state
    uninstall_agent_package()


def test_otel_collector_exists(otel_site: Site) -> None:
    assert Path(otel_site.root, "bin", "otelcol").exists()


@pytest.mark.parametrize(
    "command",
    [
        ["otelcol", "--help"],
    ],
)
def test_otel_collector_command_availability(otel_site: Site, command: list[str]) -> None:
    # Commands executed here should return with exit code 0
    otel_site.check_output(command)


def test_otel_collector_build_configuration(otel_site: Site) -> None:
    with open(
        repo_path() / "non-free" / "packages" / "otel-collector" / "builder-config.yaml"
    ) as f:
        expected_config = yaml.safe_load(f)
    actual_config = yaml.safe_load(otel_site.check_output(["otelcol", "components"]))

    assert actual_config["buildinfo"]["description"] == expected_config["dist"]["description"]

    for comp_type in ("exporters", "receivers", "processors", "extensions"):
        actual_config_for_type = sorted([a["module"] for a in actual_config[comp_type]])
        expected_config_for_type = sorted([e["gomod"] for e in expected_config[comp_type]])
        assert actual_config_for_type == expected_config_for_type


@contextmanager
def _modify_test_site(otel_site: Site, hostname: str, agent_ctl: Path) -> Iterator[None]:
    with otel_collector_enabled(otel_site):
        try:
            otel_site.openapi.hosts.create(
                hostname,
                attributes={
                    "ipaddress": "127.0.0.1",
                    "tag_agent": "cmk-agent",
                    "tag_piggyback": "no-piggyback",
                },
                folder="/",
            )
            register_controller(agent_ctl, otel_site, HostName(hostname))
            yield
        finally:
            otel_site.openapi.hosts.delete(hostname)


def test_otel_collector_self_monitoring(agent_ctl: Path, otel_site: Site) -> None:
    hostname = otel_site.id

    with _modify_test_site(otel_site, hostname, agent_ctl):
        otel_site.ensure_running()

        wait_for_opentelemetry_data(otel_site, SELF_MONITORING_HOST)

        logger.info("Running service discovery and activating changes")
        otel_site.openapi.service_discovery.run_discovery_and_wait_for_completion(hostname)
        otel_site.openapi.changes.activate_and_wait_for_completion()

        expected_service_name = f"OMD {otel_site.id} OTel collector"
        logger.info("Checking collector monitoring service is created")
        services = otel_site.get_host_services(hostname)
        assert expected_service_name in services, (
            f"{expected_service_name} was not found in host services"
        )
