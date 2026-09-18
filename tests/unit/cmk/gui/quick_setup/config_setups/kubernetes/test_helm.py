#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import replace
from typing import Literal

import pytest

from cmk.gui.quick_setup.config_setups.kubernetes.helm import monitoring_values, MonitoringSettings


def test_chart_values_preserve_monitoring_choices() -> None:
    settings = MonitoringSettings(
        cluster_name="production",
        host_name="legacy-cluster",
        host_kinds=frozenset({"nodes"}),
        namespaces=("include", ("^production$",)),
        annotations=("pattern", "^checkmk\\.com/"),
        excluded_node_roles=(),
        include_pvcs=True,
        include_cronjob_pods=True,
    )

    values = monitoring_values(settings)

    assert values == {
        "clusterName": "production",
        "clusterHostName": "legacy-cluster",
        "emitAll": {
            "pods": False,
            "namespaces": False,
            "nodes": True,
            "deployments": False,
            "daemonsets": False,
            "statefulsets": False,
            "cronjobs": False,
            "pvcs": True,
        },
        "podHosts": {"includeCronJobPods": True},
        "namespaceFilter": {"includePatterns": ["^production$"], "excludePatterns": []},
        "hostLabels": {"importAllAnnotations": False, "importKeyPattern": "^checkmk\\.com/"},
        "clusterAggregation": {"excludedNodeRolePatterns": []},
    }


def test_namespace_exclusion_does_not_also_enable_inclusion() -> None:
    settings = MonitoringSettings(
        cluster_name="cluster",
        host_name="cluster",
        host_kinds=frozenset(),
        namespaces=("exclude", ("^kube-",)),
    )

    values = monitoring_values(settings)

    assert values["namespaceFilter"] == {"includePatterns": [], "excludePatterns": ["^kube-"]}


@pytest.mark.parametrize(
    "annotations", [pytest.param("none", id="none"), pytest.param("all", id="all")]
)
def test_annotation_choice_clears_pattern(annotations: Literal["none", "all"]) -> None:
    settings = MonitoringSettings(
        cluster_name="cluster", host_name="cluster", host_kinds=frozenset()
    )

    values = monitoring_values(replace(settings, annotations=annotations))

    assert values["hostLabels"] == {
        "importAllAnnotations": annotations == "all",
        "importKeyPattern": "",
    }
