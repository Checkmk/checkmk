#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    DomainObjectModel,
)

from .dashboard import DashboardResponse


@api_model
class DashboardDomainObject(DomainObjectModel):
    domainType: Literal["dashboard"] = api_field(description="The domain type of the object.")
    extensions: DashboardResponse = api_field(description="All the data and metadata of this host.")


@api_model
class DashboardDomainObjectCollection(DomainObjectCollectionModel):
    domainType: Literal["dashboard"] = api_field(description="The domain type of the object.")
    value: list[DashboardDomainObject] = api_field(description="A list of dashboards.")
