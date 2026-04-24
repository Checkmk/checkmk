#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest
from pydantic import TypeAdapter, ValidationError

from cmk.ccc.hostaddress import HostName
from cmk.gui.openapi.api_endpoints.models.host_attribute_models import BaseHostAttributeModel
from cmk.licensing.basics.features import FeatureName


def test_parents_validator(sample_host: str) -> None:
    result = TypeAdapter(  # astrein: disable=pydantic-type-adapter
        BaseHostAttributeModel
    ).validate_python({"parents": [sample_host]})
    assert result.parents == [HostName(sample_host)]


def test_bake_agent_package_allowed_when_bakery_feature_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.openapi.framework.model.restrict_features.is_feature_enabled",
        lambda _omd_root, feature: feature is FeatureName.BAKERY,
    )

    result = TypeAdapter(  # astrein: disable=pydantic-type-adapter
        BaseHostAttributeModel
    ).validate_python({"bake_agent_package": True})

    assert result.bake_agent_package is True


def test_bake_agent_package_rejected_when_bakery_feature_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.openapi.framework.model.restrict_features.is_feature_enabled",
        lambda _omd_root, _feature: False,
    )

    with pytest.raises(
        ValidationError, match="bake_agent_package field is not supported by this license"
    ):
        TypeAdapter(  # astrein: disable=pydantic-type-adapter
            BaseHostAttributeModel
        ).validate_python({"bake_agent_package": True})
