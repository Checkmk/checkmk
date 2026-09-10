#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
from copy import deepcopy

import pytest
import yaml

from cmk.gui.quick_setup.config_setups.kubernetes.configuration import (
    pull_configuration,
    with_dcd_host_deletion,
)
from cmk.gui.quick_setup.config_setups.kubernetes.deployment import pull_deployment
from cmk.gui.quick_setup.config_setups.kubernetes.helm import MonitoringSettings
from cmk.gui.watolib.configuration_bundle_store import BundleId
from cmk.gui.watolib.configuration_bundles import CreateBundleEntities, CreateDCDConnection


def test_dcd_cleanup_preserves_source_restriction_and_timing_safeguards() -> None:
    connections = [
        CreateDCDConnection(
            id="kubernetes_config_1",
            spec={
                "site": "monitoring",
                "connector": (
                    "piggyback",
                    {
                        "source_filters": ["legacy-host"],
                        "interval": 60,
                        "creation_rules": [
                            {
                                "create_folder_path": "kubernetes",
                                "host_attributes": {"tag_agent": "no-agent"},
                                "delete_hosts": False,
                            }
                        ],
                        "discover_on_creation": True,
                        "no_deletion_time_after_init": 600,
                        "max_cache_age": 3600,
                        "validity_period": 60,
                    },
                ),
            },
        )
    ]
    original = deepcopy(connections)
    expected = deepcopy(connections)
    expected[0]["spec"]["connector"][1]["creation_rules"][0]["delete_hosts"] = True

    result = with_dcd_host_deletion(connections)

    assert result == expected
    assert connections == original


@pytest.fixture
def configuration() -> CreateBundleEntities:
    return pull_configuration(
        bundle_id=BundleId("kubernetes_config_1"),
        host_name="legacy-host",
        host_path="kubernetes",
        site_id="monitoring",
        base_url="https://kubernetes.example.com/",
        shared_secret="supplied-secret",
    )


def test_rule_references_password_entry_without_embedding_secret(
    configuration: CreateBundleEntities,
) -> None:
    assert configuration.passwords is not None
    assert configuration.rules is not None
    (password,) = configuration.passwords
    (rule,) = configuration.rules

    assert rule["spec"]["value"] == {
        "url": "https://kubernetes.example.com",
        "shared_secret": ("cmk_postprocessed", "stored_password", (password["id"], "")),
        "verify_cert": True,
    }


def test_password_entry_matches_deployed_secret(configuration: CreateBundleEntities) -> None:
    deployment = pull_deployment(
        MonitoringSettings(cluster_name="cluster", host_name="legacy-host", host_kinds=frozenset()),
        release_name="monitoring",
        namespace="checkmk-monitoring",
        shared_secret="supplied-secret",
        node_port=30050,
    )

    manifest = yaml.safe_load(deployment.files["pull-secret.yaml"])
    assert configuration.passwords is not None
    (password,) = configuration.passwords

    assert password["spec"]["password"].encode() == base64.b64decode(manifest["data"]["secret"])


def test_pull_rule_targets_source_host_and_belongs_to_bundle(
    configuration: CreateBundleEntities,
) -> None:
    assert configuration.rules is not None
    (rule,) = configuration.rules

    assert rule["ruleset"] == "special_agents:kube_v2"
    assert rule["folder"] == "kubernetes"
    assert rule["spec"]["condition"]["host_name"] == ["legacy-host"]
    assert rule["spec"]["locked_by"] == {
        "site_id": "monitoring",
        "program_id": "quick_setup",
        "instance_id": "kubernetes_config_1",
    }


def test_empty_secret_is_rejected() -> None:
    with pytest.raises(ValueError, match="shared secret must not be empty"):
        pull_configuration(
            bundle_id=BundleId("kubernetes_config_1"),
            host_name="cluster",
            host_path="",
            site_id="monitoring",
            base_url="https://kubernetes.example.com",
            shared_secret="",
        )
