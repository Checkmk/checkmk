#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
import yaml

from tests.testlib.common.repo import repo_path
from tests.testlib.site import Site
from tests.testlib.version import edition_from_env

# Apply the skipif marker to all tests in this file for non Managed or Cloud edition
pytestmark = [
    pytest.mark.skipif(
        not any([edition_from_env().is_cloud_edition(), edition_from_env().is_managed_edition()]),
        reason="otel-collector only shipped with Cloud or Managed",
    )
]


def test_otel_collector_exists(site: Site) -> None:
    assert Path(site.root, "bin", "otelcol").exists()


@pytest.mark.parametrize(
    "command",
    [
        ["otelcol", "--help"],
    ],
)
def test_otel_collector_command_availability(site: Site, command: list[str]) -> None:
    # Commands executed here should return with exit code 0
    site.check_output(command)


def test_otel_collector_build_configuration(site: Site) -> None:
    with open(
        repo_path() / "non-free" / "packages" / "otel-collector" / "builder-config.yaml"
    ) as f:
        expected_config = yaml.safe_load(f)
    actual_config = yaml.safe_load(site.check_output(["otelcol", "components"]))

    assert actual_config["buildinfo"]["description"] == expected_config["dist"]["description"]

    for comp_type in ("exporters", "receivers", "processors", "extensions"):
        actual_config_for_type = sorted([a["module"] for a in actual_config[comp_type]])
        expected_config_for_type = sorted([e["gomod"] for e in expected_config[comp_type]])
        assert actual_config_for_type == expected_config_for_type


@contextmanager
def _modify_test_site(site: Site, hostname: str) -> Iterator[None]:
    rule_id = ""
    try:
        site.set_config("OPENTELEMETRY_COLLECTOR", "on", with_restart=True)
        site.openapi.hosts.create(
            hostname,
            attributes={
                "tag_address_family": "no-ip",
                "tag_agent": "special-agents",
                "tag_piggyback": "no-piggyback",
            },
            folder="/",
        )
        rule_id = site.openapi.rules.create(
            ruleset_name="special_agents:otel",
            value={"include_self_monitoring": True},
            conditions={
                "host_name": {
                    "match_on": [hostname],
                    "operator": "one_of",
                },
            },
            folder="/",
        )
        yield
    finally:
        if rule_id:
            site.openapi.rules.delete(rule_id)
        site.openapi.hosts.delete(hostname)
        site.set_config("OPENTELEMETRY_COLLECTOR", "off", with_restart=True)


def test_otel_collector_self_monitoring(site: Site) -> None:
    hostname = "otelhost"
    with _modify_test_site(site, hostname):
        site.ensure_running()
        site.openapi.service_discovery.run_discovery_and_wait_for_completion(hostname)
        result = site.openapi.service_discovery.get_discovery_result(hostname)
    assert result["extensions"] == {
        "check_table": {},
        "host_labels": {
            "cmk/otel/metrics": {
                # Means: section is there (special agent otel was executed!) but empty.
                # First dataset will be generated 60000ms after the start
                "value": "pending",
                "plugin_name": "otel_metrics",
            }
        },
        "vanished_labels": {},
        "changed_labels": {},
    }
