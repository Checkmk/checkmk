#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    DomainObjectModel,
)


@api_model
class HostGroupExtensions:
    alias: str | ApiOmitted = api_field(
        description="The name used for displaying in the GUI.",
        example="Windows Servers",
        default_factory=ApiOmitted,
    )
    customer: str | ApiOmitted = api_field(
        description="The customer for which the object is configured.",
        example="provider",
        default_factory=ApiOmitted,
    )


@api_model
class HostGroupModel(DomainObjectModel):
    domainType: Literal["host_group_config"] = api_field(
        description="The domain type of the object.",
    )
    members: dict[str, object] = api_field(
        description="The container for external resources, like linked foreign objects or actions.",
    )
    extensions: HostGroupExtensions = api_field(
        description="All the attributes of the domain object.",
    )


@api_model
class HostGroupCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["host_group_config"] = api_field(
        description="The domain type of the objects in the collection.",
    )
    value: list[HostGroupModel] = api_field(
        description="A list of host group objects.",
    )
