#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import shlex

import pytest
import yaml

from cmk.gui.quick_setup.config_setups.kubernetes.deployment import (
    DeploymentBundle,
    pull_deployment,
    push_deployment,
)
from cmk.gui.quick_setup.config_setups.kubernetes.helm import MonitoringSettings


@pytest.fixture
def monitoring() -> MonitoringSettings:
    return MonitoringSettings(
        cluster_name="cluster", host_name="legacy-host", host_kinds=frozenset()
    )


@pytest.fixture
def bundle(monitoring: MonitoringSettings) -> DeploymentBundle:
    return pull_deployment(
        monitoring,
        release_name="monitoring",
        namespace="checkmk-monitoring",
        shared_secret="supplied-secret",
        node_port=30050,
    )


def test_pull_values_reference_the_supplied_secret_manifest(bundle: DeploymentBundle) -> None:
    values = yaml.safe_load(bundle.files["values.yaml"])
    secret = yaml.safe_load(bundle.files["pull-secret.yaml"])

    reference = values["pull"]["authentication"]["existingSecret"]

    assert reference["name"] == secret["metadata"]["name"]
    assert secret["metadata"]["namespace"] == "checkmk-monitoring"
    assert base64.b64decode(secret["data"][reference["key"]]) == b"supplied-secret"
    assert values["pull"]["authentication"]["enabled"] is True
    assert "supplied-secret" not in bundle.files["values.yaml"]
    assert "supplied-secret" not in bundle.commands


def test_pull_bundle_enables_only_pull_and_exposes_requested_port(bundle: DeploymentBundle) -> None:
    values = yaml.safe_load(bundle.files["values.yaml"])

    assert values["push"] == {"enabled": False}
    assert values["pull"]["enabled"] is True
    assert values["metricsCache"]["service"] == {"type": "NodePort", "nodePort": 30050}
    assert values["pull"]["encryption"] == {"enabled": False, "existingSecret": ""}


@pytest.mark.parametrize(
    "checkmk_version, chart_version_range",
    [
        pytest.param("2.5.0p3", "~2.5.0", id="previous-release-line"),
        pytest.param("3.0.0p1", "~3.0.0", id="patch-release"),
        pytest.param("3.0.0p42", "~3.0.0", id="later-patch-same-range"),
        pytest.param("3.0.0b1", "~3.0.0", id="beta"),
        pytest.param("3.0.0-2026.09.10", "~3.0.0", id="daily"),
    ],
)
def test_helm_command_uses_compatible_chart_range_and_generated_files(
    monitoring: MonitoringSettings,
    checkmk_version: str,
    chart_version_range: str,
) -> None:
    bundle = pull_deployment(
        monitoring,
        release_name="monitoring",
        namespace="checkmk-monitoring",
        shared_secret="supplied-secret",
        node_port=30050,
        checkmk_version=checkmk_version,
    )

    command = shlex.split(bundle.commands.splitlines()[-1])

    assert bundle.chart_version_range == chart_version_range
    assert command == [
        "helm",
        "upgrade",
        "--install",
        "monitoring",
        "oci://ghcr.io/checkmk/charts/cmk-rustik",
        "--version",
        chart_version_range,
        "--namespace",
        "checkmk-monitoring",
        "--create-namespace",
        "--values",
        "values.yaml",
    ]


def test_nodeport_tls_uses_existing_certificate(monitoring: MonitoringSettings) -> None:
    bundle = pull_deployment(
        monitoring,
        release_name="monitoring",
        namespace="checkmk-monitoring",
        shared_secret="supplied-secret",
        node_port=30050,
        tls_secret_name="external-certificate",
    )

    values = yaml.safe_load(bundle.files["values.yaml"])

    assert values["pull"]["encryption"] == {
        "enabled": True,
        "existingSecret": "external-certificate",
    }


def test_long_release_names_keep_secret_names_distinct(
    monitoring: MonitoringSettings,
) -> None:
    bundles = [
        pull_deployment(
            monitoring,
            release_name="a" * 52 + suffix,
            namespace="monitoring",
            shared_secret="supplied-secret",
            node_port=30050,
        )
        for suffix in ("x", "y")
    ]

    secrets = [yaml.safe_load(bundle.files["pull-secret.yaml"]) for bundle in bundles]

    assert secrets[0]["metadata"]["name"] != secrets[1]["metadata"]["name"]
    for bundle, secret in zip(bundles, secrets):
        values = yaml.safe_load(bundle.files["values.yaml"])
        assert (
            values["pull"]["authentication"]["existingSecret"]["name"] == secret["metadata"]["name"]
        )
        assert "fullnameOverride" not in values


def test_empty_secret_is_rejected(monitoring: MonitoringSettings) -> None:
    with pytest.raises(ValueError, match="shared secret must not be empty"):
        pull_deployment(
            monitoring,
            release_name="monitoring",
            namespace="monitoring",
            shared_secret="",
            node_port=30050,
        )


def test_version_without_release_line_is_rejected(monitoring: MonitoringSettings) -> None:
    with pytest.raises(ValueError, match="major/minor version"):
        pull_deployment(
            monitoring,
            release_name="monitoring",
            namespace="monitoring",
            shared_secret="supplied-secret",
            node_port=30050,
            checkmk_version="2022.01.01",
        )


@pytest.fixture
def push_bundle(monitoring: MonitoringSettings) -> DeploymentBundle:
    return push_deployment(
        monitoring,
        release_name="monitoring",
        namespace="checkmk-monitoring",
        receiver_url="https://receiver.example.com:8000/site",
        registration_token="supplied-token",
        site_ca_certificate="supplied-ca\n",
        checkmk_version="3.0.0p7",
    )


def test_push_enables_verified_push_and_disables_pull(push_bundle: DeploymentBundle) -> None:
    values = yaml.safe_load(push_bundle.files["values.yaml"])

    assert values["push"] == {
        "enabled": True,
        "url": "https://receiver.example.com:8000/site",
        "registrationSecret": "monitoring-push-registration",
    }
    assert values["pull"] == {"enabled": False}
    assert values["clusterHostName"] == "legacy-host"
    assert "metricsCache" not in values  # No externally exposed pull service is needed.
    assert "fullnameOverride" not in values


def test_registration_secret_matches_chart_reference(push_bundle: DeploymentBundle) -> None:
    values = yaml.safe_load(push_bundle.files["values.yaml"])
    manifest = yaml.safe_load(push_bundle.files["push-registration-secret.yaml"])

    assert manifest["metadata"] == {
        "name": values["push"]["registrationSecret"],
        "namespace": "checkmk-monitoring",
    }
    assert {key: base64.b64decode(value) for key, value in manifest["data"].items()} == {
        "token": b"supplied-token",
        "site-ca-pem": b"supplied-ca\n",
    }


def test_registration_credentials_stay_out_of_values_commands_and_repr(
    push_bundle: DeploymentBundle,
) -> None:
    exposed_text = push_bundle.files["values.yaml"] + push_bundle.commands + repr(push_bundle)

    assert "supplied-token" not in exposed_text
    assert "supplied-ca" not in exposed_text
    assert base64.b64encode(b"supplied-token").decode() not in exposed_text


def test_install_applies_registration_secret_before_helm(push_bundle: DeploymentBundle) -> None:
    commands = [shlex.split(line) for line in push_bundle.commands.splitlines()]

    assert len(commands) == 3
    assert commands[1] == ["kubectl", "apply", "-f", "push-registration-secret.yaml"]
    assert commands[2] == [
        "helm",
        "upgrade",
        "--install",
        "monitoring",
        "oci://ghcr.io/checkmk/charts/cmk-rustik",
        "--version",
        "~3.0.0",
        "--namespace",
        "checkmk-monitoring",
        "--create-namespace",
        "--values",
        "values.yaml",
    ]


@pytest.mark.parametrize(
    "token, certificate",
    [
        pytest.param("", "supplied-ca", id="missing-token"),
        pytest.param("supplied-token", "", id="missing-ca"),
    ],
)
def test_incomplete_registration_credentials_are_rejected(
    monitoring: MonitoringSettings, token: str, certificate: str
) -> None:
    with pytest.raises(ValueError, match="requires a token and site CA certificate"):
        push_deployment(
            monitoring,
            release_name="monitoring",
            namespace="checkmk-monitoring",
            receiver_url="https://receiver.example.com:8000/site",
            registration_token=token,
            site_ca_certificate=certificate,
        )
