#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal

from cmk.ccc.user import UserId
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    DomainObjectModel,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.type_defs import AnnotatedUserId

from ..store import get_permitted_dashboards
from ._family import DASHBOARD_FAMILY
from ._utils import dashboard_uses_relative_grid, PERMISSIONS_DASHBOARD

type DashboardLayoutType = Literal["relative_grid", "responsive_grid"]


@api_model
class DashboardDisplay:
    """Display and presentation settings for dashboard listings."""

    title: str = api_field(description="The title of the dashboard")
    topic: str = api_field(description="Topic area the dashboard covers")
    hidden: bool = api_field(description="Whether the dashboard is hidden from general listings")
    sort_index: int = api_field(description="Numeric value used for ordering dashboards in lists.")


@api_model
class DashboardMetadata:
    """Complete metadata configuration for dashboard instances."""

    name: str = api_field(description="Unique identifier for the dashboard.")
    owner: AnnotatedUserId | None = api_field(
        description="Owner of the dashboard or null if the dashboard is built-in."
    )
    is_built_in: bool = api_field(
        description="Whether the dashboard is a built-in (system) dashboard."
    )
    is_editable: bool = api_field(
        description="Whether the user can edit the dashboard.",
    )
    layout_type: DashboardLayoutType = api_field(
        description="Layout system used: 'relative' for absolute positioning, 'responsive' for adaptive design."
    )
    display: DashboardDisplay = api_field(description="Display and presentation preferences.")


@api_model
class DashboardMetadataModel(DomainObjectModel):
    domainType: Literal["dashboard_metadata"] = api_field(
        description="The domain type of the object."
    )
    extensions: DashboardMetadata = api_field(description="The metadata of this dashboard.")


@api_model
class DashboardMetadataCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["dashboard_metadata"] = api_field(
        description="The domain type of the objects in the collection",
        example="dashboard",
    )
    # TODO: add proper example
    value: list[DashboardMetadataModel] = api_field(
        description="A list of host objects", example=""
    )


def list_dashboard_metadata_v1() -> DashboardMetadataCollectionModel:
    """List permitted dashboard metadata."""
    dashboards = []
    for dashboard_id, dashboard in get_permitted_dashboards().items():
        # Determine layout type based on dashboard configuration
        layout_type: DashboardLayoutType = (
            "relative_grid" if dashboard_uses_relative_grid(dashboard) else "responsive_grid"
        )

        display = DashboardDisplay(
            title=str(dashboard["title"]),
            topic=dashboard["topic"],
            hidden=dashboard["hidden"],
            sort_index=dashboard["sort_index"],
        )
        is_built_in = dashboard["owner"] == UserId.builtin()
        # Note: from legacy build page header code it seems that permission edit_foreign_dashboards
        # are not taken into account to determine if the user is allowed to edit a dashboard.
        # This could be changed in the future.
        is_editable = (
            not is_built_in
            and user.may("general.edit_dashboards")
            and dashboard["owner"] == user.id
        )
        metadata = DashboardMetadata(
            name=dashboard["name"],
            owner=dashboard["owner"] if dashboard["owner"] != UserId.builtin() else None,
            is_built_in=is_built_in,
            is_editable=is_editable,
            layout_type=layout_type,
            display=display,
        )
        dashboard_model = DashboardMetadataModel(
            id=dashboard_id,
            domainType="dashboard_metadata",
            extensions=metadata,
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
