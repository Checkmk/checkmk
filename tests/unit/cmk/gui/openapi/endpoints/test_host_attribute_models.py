#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pydantic import TypeAdapter

from cmk.ccc.hostaddress import HostName
from cmk.gui.openapi.api_endpoints.models.host_attribute_models import BaseHostAttributeModel


def test_parents_validator(sample_host: str) -> None:
    result = TypeAdapter(  # astrein: disable=pydantic-type-adapter
        BaseHostAttributeModel
    ).validate_python({"parents": [sample_host]})
    assert result.parents == [HostName(sample_host)]
