#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href

from ...openapi.framework.model.base_models import LinkModel
from ..store import get_permitted_dashboards
from ._family import DASHBOARD_FAMILY
from ._model.dashboard import DashboardResponse
from ._model.response_model import DashboardDomainObjectCollection
from ._utils import PERMISSIONS_DASHBOARD, serialize_dashboard


def list_dashboards_v1() -> DashboardDomainObjectCollection:
    """List all available dashboards."""
    dashboards = get_permitted_dashboards()
    return DashboardDomainObjectCollection(
        domainType="dashboard",
        id="dashboard",
        value=[
            serialize_dashboard(dashboard_id, DashboardResponse.from_internal(dashboard))
            for dashboard_id, dashboard in dashboards.items()
        ],
        links=[LinkModel.create("self", collection_href("dashboard"))],
    )


ENDPOINT_LIST_DASHBOARDS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("dashboard"),
        link_relation="cmk/list",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_DASHBOARD),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=list_dashboards_v1)},
)
