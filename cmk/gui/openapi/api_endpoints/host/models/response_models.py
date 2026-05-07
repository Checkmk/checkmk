#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    DomainObjectModel,
)
from cmk.gui.openapi.framework.model.common_fields import LivestatusValue


@api_model
class HostStatusObjectModel(DomainObjectModel):
    domainType: Literal["host"] = api_field(description="The domain type of the object")
    extensions: dict[str, LivestatusValue] = api_field(description="The attributes of the host")


@api_model
class HostStatusCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["host"] = api_field(
        description="The domain type of the objects in the collection"
    )
    value: list[HostStatusObjectModel] = api_field(description="A list of host status objects")
