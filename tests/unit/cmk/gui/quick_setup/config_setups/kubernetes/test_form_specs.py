#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.form_specs import (
    DEFAULT_VALUE,
    get_visitor,
    RawDiskData,
    RawFrontendData,
    VisitorOptions,
)
from cmk.gui.quick_setup.config_setups.kubernetes.form_specs import (
    advanced_configuration,
    cluster_configuration,
)
from cmk.gui.quick_setup.config_setups.kubernetes.helm import HOST_KINDS
from cmk.rulesets.v1.form_specs import MultipleChoice

pytestmark = pytest.mark.usefixtures("request_context")


def test_host_kind_choices_match_supported_kinds() -> None:
    spec = cluster_configuration()

    host_kinds = spec.elements["host_kinds"].parameter_form

    assert isinstance(host_kinds, MultipleChoice)
    assert {element.name for element in host_kinds.elements} == set(HOST_KINDS)


def test_cluster_form_prefills_deployment_namespace_and_non_pod_kinds() -> None:
    visitor = get_visitor(
        cluster_configuration(), VisitorOptions(migrate_values=True, mask_values=False)
    )

    _spec, frontend_values = visitor.to_vue(DEFAULT_VALUE)
    values = visitor.to_disk(RawFrontendData(frontend_values))

    assert values == {
        "cluster_name": "",
        "namespace": "checkmk-monitoring",
        "host_kinds": [
            "cronjobs",
            "daemonsets",
            "deployments",
            "namespaces",
            "nodes",
            "statefulsets",
        ],
        "namespaces": None,
    }


@pytest.mark.parametrize(
    "field, value",
    [
        pytest.param("cluster_name", "", id="missing-cluster"),
        pytest.param("cluster_name", "a/b", id="invalid-host-name-character"),
        pytest.param("cluster_name", "-production", id="leading-hyphen"),
        pytest.param("cluster_name", ".production", id="leading-dot"),
        pytest.param("cluster_name", "production\n", id="trailing-newline"),
        pytest.param("namespace", "Monitoring", id="uppercase-namespace"),
        pytest.param("namespace", "monitoring_1", id="underscore-in-namespace"),
        pytest.param("namespace", "a" * 64, id="namespace-too-long"),
        pytest.param("namespace", "monitoring\n", id="namespace-trailing-newline"),
        pytest.param("namespaces", ("include", []), id="empty-namespace-filter"),
        pytest.param("namespaces", ("exclude", ["["]), id="invalid-namespace-pattern"),
    ],
)
def test_invalid_cluster_settings_are_rejected(field: str, value: object) -> None:
    visitor = get_visitor(
        cluster_configuration(), VisitorOptions(migrate_values=True, mask_values=False)
    )
    settings: dict[str, object] = {
        "cluster_name": "production",
        "namespace": "monitoring",
        "host_kinds": [],
        "namespaces": None,
    }
    assert not visitor.validate(RawDiskData(settings))

    errors = visitor.validate(RawDiskData({**settings, field: value}))

    assert errors


@pytest.mark.parametrize(
    "mode", [pytest.param("include", id="include"), pytest.param("exclude", id="exclude")]
)
def test_namespace_filter_preserves_selected_mode(mode: str) -> None:
    visitor = get_visitor(
        cluster_configuration(), VisitorOptions(migrate_values=True, mask_values=False)
    )
    settings = {
        "cluster_name": "production",
        "namespace": "monitoring",
        "host_kinds": [],
        "namespaces": (mode, ["^prod-", "^monitoring$"]),
    }

    assert not visitor.validate(RawDiskData(settings))
    assert visitor.to_disk(RawDiskData(settings)) == settings


def test_advanced_defaults_exclude_infrastructure_roles_without_importing_annotations() -> None:
    visitor = get_visitor(
        advanced_configuration(), VisitorOptions(migrate_values=True, mask_values=False)
    )

    _spec, values = visitor.to_vue(DEFAULT_VALUE)

    assert values == {"excluded_node_roles": ["control-plane", "infra"], "annotations": None}


@pytest.mark.parametrize(
    "annotations",
    [
        pytest.param(("all", None), id="all"),
        pytest.param(("pattern", "^example\\.com/"), id="pattern"),
    ],
)
def test_advanced_options_allow_all_nodes_and_annotation_import(annotations: object) -> None:
    visitor = get_visitor(
        advanced_configuration(), VisitorOptions(migrate_values=True, mask_values=False)
    )
    settings = {"excluded_node_roles": [], "annotations": annotations}

    assert not visitor.validate(RawDiskData(settings))
    assert visitor.to_disk(RawDiskData(settings)) == settings
