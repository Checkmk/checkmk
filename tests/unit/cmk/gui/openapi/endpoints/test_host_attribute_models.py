#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import cast

import pytest
from pydantic import TypeAdapter

from cmk.ccc.hostaddress import HostName
from cmk.gui.openapi.api_endpoints.models.host_attribute_models import (
    BaseHostAttributeModel,
    HostViewAttributeModel,
)
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.watolib.host_attributes import HostAttributes


def test_parents_validator(sample_host: str) -> None:
    result = TypeAdapter(  # astrein: disable=pydantic-type-adapter
        BaseHostAttributeModel
    ).validate_python({"parents": [sample_host]})
    assert result.parents == [HostName(sample_host)]


@pytest.mark.xfail(
    strict=True, raises=(AttributeError, TypeError), reason="crash groups 4850, 4878"
)
@pytest.mark.parametrize(
    "attribute",
    ["snmp_community", "management_snmp_community", "management_ipmi_credentials"],
)
def test_credentials_stored_as_none_are_left_out(attribute: str) -> None:
    model = HostViewAttributeModel.from_internal(cast(HostAttributes, {attribute: None}), set())

    assert isinstance(getattr(model, attribute), ApiOmitted)
