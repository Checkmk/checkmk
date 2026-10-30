#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from typing import Annotated

from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href

from ..metadata import DashboardMetadataObject
from ..store import get_permitted_dashboards, get_permitted_dashboards_by_owners
from ..type_defs import DashboardConfig, DashboardName
from ._family import DASHBOARD_FAMILY
from ._utils import PERMISSIONS_DASHBOARD
from .model.metadata import (
    DashboardMetadata,
    DashboardMetadataCollectionModel,
    DashboardMetadataModel,
)


def list_dashboard_metadata_v1(
    api_context: ApiContext,
    all_owners: Annotated[
        bool,
        QueryParam(
            description=(
                "List every copy of a dashboard the user may see, one per owner, instead of the "
                "one copy each dashboard name resolves to. Several entries then share an ID."
            ),
            example="False",
        ),
    ] = False,
) -> DashboardMetadataCollectionModel:
    """List permitted dashboard metadata."""
    dashboards = []
    user_permissions = api_context.config.user_permissions()
    configs: Iterable[tuple[DashboardName, DashboardConfig]]
    if all_owners:
        configs = (
            (dashboard_id, dashboard)
            for dashboard_id, copies in get_permitted_dashboards_by_owners().items()
            for dashboard in copies.values()
        )
    else:
        configs = get_permitted_dashboards().items()
    for dashboard_id, dashboard in configs:
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
