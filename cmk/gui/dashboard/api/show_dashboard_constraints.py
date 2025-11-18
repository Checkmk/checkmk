#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from typing import Literal

from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import DomainObjectModel
from cmk.gui.openapi.restful_objects.constructors import object_href

from ._family import DASHBOARD_FAMILY
from ._utils import DashboardConstants
from .model.constants import (
    DashboardConstantsResponse,
)


@api_model
class DashboardConstantsObject(DomainObjectModel):
    domainType: Literal["constant"] = api_field(description="The domain type of the object.")
    extensions: DashboardConstantsResponse = api_field(
        description="All the constants data of a dashboard."
    )


def show_dashboard_constants_v1() -> DashboardConstantsObject:
    """Show the dashboard constraints"""
    return DashboardConstantsObject(
        domainType="constant",
        id="dashboard",
        title="Dashboard Constants",
        links=[],
        extensions=DashboardConstants.generate_api_response(),
    )


ENDPOINT_SHOW_DASHBOARD_CONSTANTS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("constant", "dashboard"),
        link_relation="cmk/fetch",
        method="get",
    ),
    permissions=EndpointPermissions(),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=show_dashboard_constants_v1)},
)
