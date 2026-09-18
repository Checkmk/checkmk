#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import shlex
from collections.abc import Mapping
from dataclasses import dataclass, field

import yaml

from cmk.ccc.version import __version__, Version

from .helm import monitoring_values, MonitoringSettings

CHART_REFERENCE = "oci://ghcr.io/checkmk/charts/cmk-rustik"


@dataclass(frozen=True, kw_only=True)
class DeploymentBundle:
    files: dict[str, str] = field(repr=False)
    commands: str
    chart_version_range: str


def pull_deployment(
    monitoring: MonitoringSettings,
    *,
    release_name: str,
    namespace: str,
    shared_secret: str,
    node_port: int,
    tls_secret_name: str = "",
    checkmk_version: str = __version__,
) -> DeploymentBundle:
    """Generate an authenticated pull deployment and installation commands.

    The caller validates deployment settings and persists the shared secret in the password store.
    """
    if not shared_secret:
        raise ValueError("The pull shared secret must not be empty")
    secret_name = f"{release_name}-pull-secret"
    return _deployment_bundle(
        values=_pull_values(monitoring, secret_name, node_port, tls_secret_name),
        secret=_secret_manifest(secret_name, namespace, {"secret": shared_secret}),
        secret_filename="pull-secret.yaml",
        release_name=release_name,
        namespace=namespace,
        checkmk_version=checkmk_version,
    )


def push_deployment(
    monitoring: MonitoringSettings,
    *,
    release_name: str,
    namespace: str,
    receiver_url: str,
    registration_token: str,
    site_ca_certificate: str,
    checkmk_version: str = __version__,
) -> DeploymentBundle:
    """Generate push deployment files from validated settings and supplied registration credentials."""
    if not registration_token or not site_ca_certificate:
        raise ValueError("Push registration requires a token and site CA certificate")

    secret_name = f"{release_name}-push-registration"
    return _deployment_bundle(
        values={
            **monitoring_values(monitoring),
            "push": {
                "enabled": True,
                "url": receiver_url,
                "registrationSecret": secret_name,
            },
            "pull": {"enabled": False},
        },
        secret=_secret_manifest(
            secret_name,
            namespace,
            {"token": registration_token, "site-ca-pem": site_ca_certificate},
        ),
        secret_filename="push-registration-secret.yaml",
        release_name=release_name,
        namespace=namespace,
        checkmk_version=checkmk_version,
    )


def _deployment_bundle(
    *,
    values: Mapping[str, object],
    secret: Mapping[str, object],
    secret_filename: str,
    release_name: str,
    namespace: str,
    checkmk_version: str,
) -> DeploymentBundle:
    version_base = Version.from_str(checkmk_version).base
    if version_base is None:
        raise ValueError("The chart version requires a Checkmk release with a major/minor version")
    # Chart and Checkmk patch versions advance independently within the same major/minor line.
    chart_version_range = f"~{version_base.major}.{version_base.minor}.0"
    return DeploymentBundle(
        files={
            "values.yaml": yaml.safe_dump(dict(values), sort_keys=False),
            secret_filename: yaml.safe_dump(dict(secret), sort_keys=False),
        },
        commands=_installation_commands(
            release_name, namespace, chart_version_range, secret_filename
        ),
        chart_version_range=chart_version_range,
    )


def _pull_values(
    monitoring: MonitoringSettings, secret_name: str, node_port: int, tls_secret_name: str
) -> dict[str, object]:
    return {
        **monitoring_values(monitoring),
        "push": {"enabled": False},
        "pull": {
            "enabled": True,
            "authentication": {
                "enabled": True,
                "existingSecret": {"name": secret_name, "key": "secret"},
            },
            "encryption": {"enabled": bool(tls_secret_name), "existingSecret": tls_secret_name},
        },
        "metricsCache": {"service": {"type": "NodePort", "nodePort": node_port}},
    }


def _secret_manifest(
    secret_name: str, namespace: str, data: Mapping[str, str]
) -> dict[str, object]:
    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": secret_name, "namespace": namespace},
        "type": "Opaque",
        "data": {
            key: base64.b64encode(value.encode()).decode("ascii") for key, value in data.items()
        },
    }


def _installation_commands(
    release_name: str, namespace: str, chart_version_range: str, secret_filename: str
) -> str:
    return "\n".join(
        [
            (
                f"kubectl create namespace {shlex.quote(namespace)} "
                "--dry-run=client --output=yaml | kubectl apply -f -"
            ),
            f"kubectl apply -f {shlex.quote(secret_filename)}",
            shlex.join(
                [
                    "helm",
                    "upgrade",
                    "--install",
                    release_name,
                    CHART_REFERENCE,
                    "--version",
                    chart_version_range,
                    "--namespace",
                    namespace,
                    "--create-namespace",
                    "--values",
                    "values.yaml",
                ]
            ),
        ]
    )
