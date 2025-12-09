#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"


from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href

from ..metadata import DashboardMetadataObject
from ..store import get_permitted_dashboards
from ._family import DASHBOARD_FAMILY
from ._utils import PERMISSIONS_DASHBOARD
from .model.metadata import (
    DashboardMetadata,
    DashboardMetadataCollectionModel,
    DashboardMetadataModel,
)


def list_dashboard_metadata_v1(api_context: ApiContext) -> DashboardMetadataCollectionModel:
    """List permitted dashboard metadata."""
    dashboards = []
    user_permissions = api_context.config.user_permissions()
    for dashboard_id, dashboard in get_permitted_dashboards().items():
        dashboard_model = DashboardMetadataModel(
            id=dashboard_id,
            domainType="dashboard_metadata",
            extensions=DashboardMetadata.from_dashboard_metadata_object(
                DashboardMetadataObject.from_dashboard_config(dashboard, user_permissions)
            ),
            links=[],
        )

        dashboards.append(dashboard_model)

    return DashboardMetadataCollectionModel(
        id="dashboard_metadata", domainType="dashboard_metadata", links=[], value=dashboards
    )


ENDPOINT_LIST_DASHBOARD_METADATA = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("dashboard_metadata"),
        link_relation="cmk/list",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_DASHBOARD),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=list_dashboard_metadata_v1)},
)
