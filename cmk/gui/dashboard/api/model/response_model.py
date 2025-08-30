#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import DomainObjectModel

from .dashboard import RelativeGridDashboardResponse


@api_model
class RelativeGridDashboardDomainObject(DomainObjectModel):
    domainType: Literal["dashboard"] = api_field(description="The domain type of the object.")
    extensions: RelativeGridDashboardResponse = api_field(
        description="All the data about this dashboard."
    )
