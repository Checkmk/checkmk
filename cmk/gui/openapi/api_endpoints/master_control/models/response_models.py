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


@api_model
class MasterControlExtensionsModel:
    notifications: bool = api_field(
        description="Whether notifications are enabled on the site.",
        example=True,
    )


@api_model
class MasterControlModel(DomainObjectModel):
    domainType: Literal["master_control"] = api_field(
        description="The domain type of the object.",
    )
    extensions: MasterControlExtensionsModel = api_field(
        description="The master control settings of the site.",
    )


@api_model
class MasterControlCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["master_control"] = api_field(
        description="The domain type of the objects in the collection.",
    )
    value: list[MasterControlModel] = api_field(
        description="A list of master control objects, one per site.",
    )
