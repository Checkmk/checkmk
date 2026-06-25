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
    HostUpdateAttributeModel,
    HostViewAttributeModel,
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


def test_metrics_association_accepts_multi_rule_filter_groups(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: a multi-rule ``metrics_association`` (carrying ``attribute_filter_groups``) must
    validate and round-trip to the internal structure.

    Hosts produced by more than one DCD host name lookup rule store one filter group per rule under
    ``attribute_filter_groups``. The schema previously declared only ``attribute_filters``, so the
    REST API rejected the create request and the Dynamic Host Management connection could not create
    such hosts.
    """
    monkeypatch.setattr(
        "cmk.gui.openapi.framework.model.restrict_editions.edition",
        lambda _omd_root: Edition.ULTIMATE,
    )
    payload = {
        "metrics_association": {
            "attribute_filters": {
                "resource_attributes": [{"key": "k8s.namespace.name", "value": "blog"}],
                "scope_attributes": [],
                "data_point_attributes": [],
            },
            "attribute_filter_groups": [
                {
                    "resource_attributes": [{"key": "k8s.pod.name", "value": "pod-a"}],
                    "scope_attributes": [],
                    "data_point_attributes": [],
                },
                {
                    "resource_attributes": [{"key": "k8s.pod.name", "value": "pod-b"}],
                    "scope_attributes": [],
                    "data_point_attributes": [],
                },
            ],
        }
    }

    model = TypeAdapter(  # astrein: disable=pydantic-type-adapter
        HostUpdateAttributeModel
    ).validate_python(payload)

    assert model.to_internal()["metrics_association"] == (
        "enabled",
        {
            "attribute_filters": {
                "resource_attributes": [{"key": "k8s.namespace.name", "value": "blog"}],
                "scope_attributes": [],
                "data_point_attributes": [],
            },
            "attribute_filter_groups": [
                {
                    "resource_attributes": [{"key": "k8s.pod.name", "value": "pod-a"}],
                    "scope_attributes": [],
                    "data_point_attributes": [],
                },
                {
                    "resource_attributes": [{"key": "k8s.pod.name", "value": "pod-b"}],
                    "scope_attributes": [],
                    "data_point_attributes": [],
                },
            ],
        },
    )


def test_metrics_association_view_exposes_multi_rule_filter_groups() -> None:
    """The view model exposes ``attribute_filter_groups`` for hosts produced by several rules."""
    internal_value = {
        "metrics_association": (
            "enabled",
            {
                "attribute_filters": {
                    "resource_attributes": [],
                    "scope_attributes": [],
                    "data_point_attributes": [],
                },
                "attribute_filter_groups": [
                    {
                        "resource_attributes": [{"key": "k8s.pod.name", "value": "pod-a"}],
                        "scope_attributes": [],
                        "data_point_attributes": [],
                    },
                ],
            },
        )
    }

    model = HostViewAttributeModel.from_internal(internal_value, set())  # type: ignore[arg-type]

    assert not isinstance(model.metrics_association, (ApiOmitted, str))
    groups = model.metrics_association.attribute_filter_groups
    assert not isinstance(groups, ApiOmitted)
    assert [(f.key, f.value) for f in groups[0].resource_attributes] == [("k8s.pod.name", "pod-a")]
