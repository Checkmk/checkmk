#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest
from pydantic import TypeAdapter, ValidationError

from cmk.ccc.version import Edition
from cmk.gui.config import Config
from cmk.gui.logged_in import LoggedInNobody
from cmk.gui.openapi.api_endpoints.models.folder_attribute_models import BaseFolderAttributeModel
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.licensing.basics.options import OptionName
from tests.testlib.unit.gui.validation_context import make_validation_context


def test_parents_validator(sample_host: str) -> None:
    result = TypeAdapter(  # astrein: disable=pydantic-type-adapter
        BaseFolderAttributeModel
    ).validate_python(
        {"parents": [sample_host]}, context=make_validation_context(Config(), LoggedInNobody())
    )
    assert result.parents == [sample_host]


def test_bake_agent_package_allowed_when_bakery_feature_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.openapi.framework.model.restrict_features.is_option_enabled",
        lambda _omd_root, option: option is OptionName.BAKERY,
    )

    result = TypeAdapter(  # astrein: disable=pydantic-type-adapter
        BaseFolderAttributeModel
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
            BaseFolderAttributeModel
        ).validate_python({"bake_agent_package": True})


def test_metrics_association_enabled_multi_rule_validates_and_exposes_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
        BaseFolderAttributeModel
    ).validate_python(payload)

    assert not isinstance(model.metrics_association, ApiOmitted)
    status, config = model.metrics_association
    assert status == "enabled"
    assert config is not None
    rules = config.host_name_lookup_rules
    assert [(f.key, f.value) for f in rules[0].resource_attributes] == [("k8s.pod.name", "pod-a")]
    assert [(f.key, f.value) for f in rules[1].resource_attributes] == [("k8s.pod.name", "pod-b")]
    assert rules[1].host_name_template == "$RESOURCE_ATTR.k8s.pod.name$"


def test_metrics_association_disabled_validates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.gui.openapi.framework.model.restrict_editions.edition",
        lambda _omd_root: Edition.ULTIMATE,
    )

    model = TypeAdapter(  # astrein: disable=pydantic-type-adapter
        BaseFolderAttributeModel
    ).validate_python({"metrics_association": ["disabled", None]})

    assert model.metrics_association == ("disabled", None)


def test_metrics_association_empty_lookup_rules_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.openapi.framework.model.restrict_editions.edition",
        lambda _omd_root: Edition.ULTIMATE,
    )

    with pytest.raises(ValidationError):
        TypeAdapter(  # astrein: disable=pydantic-type-adapter
            BaseFolderAttributeModel
        ).validate_python({"metrics_association": ["enabled", {"host_name_lookup_rules": []}]})


def test_metrics_association_rejected_in_unsupported_edition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.openapi.framework.model.restrict_editions.edition",
        lambda _omd_root: Edition.COMMUNITY,
    )

    with pytest.raises(ValidationError, match="not supported by this edition"):
        TypeAdapter(  # astrein: disable=pydantic-type-adapter
            BaseFolderAttributeModel
        ).validate_python({"metrics_association": ["disabled", None]})
