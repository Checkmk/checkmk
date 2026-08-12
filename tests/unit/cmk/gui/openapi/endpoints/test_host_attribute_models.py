#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest
from pydantic import TypeAdapter, ValidationError

from cmk.ccc.hostaddress import HostName
from cmk.ccc.version import Edition
from cmk.gui.openapi.api_endpoints.models.host_attribute_models import (
    BaseHostAttributeModel,
    HostAttributeRequestModel,
    HostAttributeResponseModel,
)
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.licensing.basics.options import OptionName


def test_parents_validator(sample_host: str) -> None:
    result = TypeAdapter(  # astrein: disable=pydantic-type-adapter
        BaseHostAttributeModel
    ).validate_python({"parents": [sample_host]})
    assert result.parents == [HostName(sample_host)]


def test_bake_agent_package_allowed_when_bakery_feature_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.openapi.framework.model.restrict_features.is_option_enabled",
        lambda _omd_root, option: option is OptionName.BAKERY,
    )

    result = TypeAdapter(  # astrein: disable=pydantic-type-adapter
        BaseHostAttributeModel
    ).validate_python({"bake_agent_package": True})

    assert result.bake_agent_package is True


def test_bake_agent_package_rejected_when_bakery_feature_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.openapi.framework.model.restrict_features.is_option_enabled",
        lambda _omd_root, _option: False,
    )

    with pytest.raises(
        ValidationError, match="bake_agent_package field is not supported by this license"
    ):
        TypeAdapter(  # astrein: disable=pydantic-type-adapter
            BaseHostAttributeModel
        ).validate_python({"bake_agent_package": True})


def test_metrics_association_multi_rule_request_maps_to_lookup_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A request carrying several host name lookup rules validates and maps to the internal
    ``host_name_lookup_rules`` list, preserving each rule's template."""
    monkeypatch.setattr(
        "cmk.gui.openapi.framework.model.restrict_editions.edition",
        lambda _omd_root: Edition.ULTIMATE,
    )
    payload = {
        "metrics_association": [
            "enabled",
            {
                "host_name_lookup_rules": [
                    {
                        "resource_attributes": [{"key": "k8s.pod.name", "value": "pod-a"}],
                        "scope_attributes": [],
                        "data_point_attributes": [],
                        "host_name_template": "$RESOURCE_ATTR.k8s.pod.name$",
                    },
                    {
                        "resource_attributes": [{"key": "k8s.pod.name", "value": "pod-b"}],
                        "scope_attributes": [],
                        "data_point_attributes": [],
                        "host_name_template": "$RESOURCE_ATTR.k8s.pod.name$",
                    },
                ],
            },
        ]
    }

    model = TypeAdapter(  # astrein: disable=pydantic-type-adapter
        HostAttributeRequestModel
    ).validate_python(payload)

    assert model.to_internal()["metrics_association"] == (
        "enabled",
        {
            "host_name_lookup_rules": [
                {
                    "resource_attributes": [{"key": "k8s.pod.name", "value": "pod-a"}],
                    "scope_attributes": [],
                    "data_point_attributes": [],
                    "host_name_template": "$RESOURCE_ATTR.k8s.pod.name$",
                },
                {
                    "resource_attributes": [{"key": "k8s.pod.name", "value": "pod-b"}],
                    "scope_attributes": [],
                    "data_point_attributes": [],
                    "host_name_template": "$RESOURCE_ATTR.k8s.pod.name$",
                },
            ],
        },
    )


def test_metrics_association_wire_attribute_filter_request_projects_to_three_lists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A rule's wire ``attribute_filter`` projects its ``equals`` conditions into the three
    per-kind lists. Regression test for CMK-37860."""
    monkeypatch.setattr(
        "cmk.gui.openapi.framework.model.restrict_editions.edition",
        lambda _omd_root: Edition.ULTIMATE,
    )
    payload = {
        "metrics_association": [
            "enabled",
            {
                "host_name_lookup_rules": [
                    {
                        "resource_attributes": [],
                        "scope_attributes": [],
                        "data_point_attributes": [],
                        "attribute_filter": {
                            "type": "and",
                            "conjuncts": [
                                {
                                    "type": "equals",
                                    "key": {"kind": "resource", "name": "k8s.pod.name"},
                                    "value": "pod-a",
                                },
                                {
                                    "type": "equals",
                                    "key": {"kind": "data_point", "name": "unit"},
                                    "value": "bytes",
                                },
                            ],
                        },
                        "host_name_template": "$RESOURCE_ATTR.k8s.pod.name$",
                    },
                ],
            },
        ]
    }

    model = TypeAdapter(  # astrein: disable=pydantic-type-adapter
        HostAttributeRequestModel
    ).validate_python(payload)

    assert model.to_internal()["metrics_association"] == (
        "enabled",
        {
            "host_name_lookup_rules": [
                {
                    "resource_attributes": [{"key": "k8s.pod.name", "value": "pod-a"}],
                    "scope_attributes": [],
                    "data_point_attributes": [{"key": "unit", "value": "bytes"}],
                    "host_name_template": "$RESOURCE_ATTR.k8s.pod.name$",
                },
            ],
        },
    )


def test_metrics_association_non_equals_wire_attribute_filter_request_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A wire ``attribute_filter`` richer than an AND of ``equals`` is rejected."""
    monkeypatch.setattr(
        "cmk.gui.openapi.framework.model.restrict_editions.edition",
        lambda _omd_root: Edition.ULTIMATE,
    )
    payload = {
        "metrics_association": [
            "enabled",
            {
                "host_name_lookup_rules": [
                    {
                        "resource_attributes": [],
                        "scope_attributes": [],
                        "data_point_attributes": [],
                        "attribute_filter": {
                            "type": "and",
                            "conjuncts": [
                                {
                                    "type": "regex",
                                    "key": {"kind": "resource", "name": "k8s.pod.name"},
                                    "value": "pod-.*",
                                },
                            ],
                        },
                    },
                ],
            },
        ]
    }

    model = TypeAdapter(  # astrein: disable=pydantic-type-adapter
        HostAttributeRequestModel
    ).validate_python(payload)

    with pytest.raises(ValueError, match="Expected an 'equals' attribute filter condition"):
        model.to_internal()


def test_metrics_association_empty_lookup_rules_request_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An enabled association always names at least one host name lookup rule, so an empty list
    is rejected."""
    monkeypatch.setattr(
        "cmk.gui.openapi.framework.model.restrict_editions.edition",
        lambda _omd_root: Edition.ULTIMATE,
    )
    payload = {
        "metrics_association": [
            "enabled",
            {
                "host_name_lookup_rules": [],
            },
        ]
    }

    with pytest.raises(ValidationError):
        TypeAdapter(  # astrein: disable=pydantic-type-adapter
            HostAttributeRequestModel
        ).validate_python(payload)


def test_metrics_association_view_multi_rule_exposes_all_rules_with_templates() -> None:
    """A host stored with several lookup rules is exposed as one ``host_name_lookup_rules`` entry
    per rule, each carrying its template."""
    internal_value = {
        "metrics_association": (
            "enabled",
            {
                "host_name_lookup_rules": [
                    {
                        "resource_attributes": [{"key": "k8s.pod.name", "value": "pod-a"}],
                        "scope_attributes": [],
                        "data_point_attributes": [],
                        "host_name_template": "$RESOURCE_ATTR.k8s.pod.name$",
                    },
                    {
                        "resource_attributes": [{"key": "k8s.pod.name", "value": "pod-b"}],
                        "scope_attributes": [],
                        "data_point_attributes": [],
                        "host_name_template": "$RESOURCE_ATTR.k8s.pod.name$",
                    },
                ],
            },
        )
    }

    model = HostAttributeResponseModel.from_internal(internal_value, set())  # type: ignore[arg-type]

    assert not isinstance(model.metrics_association, ApiOmitted)
    status, config = model.metrics_association
    assert status == "enabled"
    assert config is not None
    rules = config.host_name_lookup_rules
    assert [(f.key, f.value) for f in rules[0].resource_attributes] == [("k8s.pod.name", "pod-a")]
    assert [(f.key, f.value) for f in rules[1].resource_attributes] == [("k8s.pod.name", "pod-b")]
    assert rules[1].host_name_template == "$RESOURCE_ATTR.k8s.pod.name$"
