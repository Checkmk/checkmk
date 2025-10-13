#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from typing import Literal

from cmk.gui.openapi.framework import (
    ApiContext,
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

from ..metadata import DashboardLayoutType, DashboardMetadataObject
from ..store import get_permitted_dashboards
from ._family import DASHBOARD_FAMILY
from ._utils import PERMISSIONS_DASHBOARD


@api_model
class BreadcrumbItem:
    title: str = api_field(description="The title of the breadcrumb item")
    link: str | None = api_field(description="The link of the breadcrumb item")


@api_model
class Topic:
    name: str = api_field(description="Id of the topic")
    breadcrumb: list[BreadcrumbItem] = api_field(description="Breadcrumb navigation for the topic.")


@api_model
class DashboardDisplay:
    """Display and presentation settings for dashboard listings."""

    title: str = api_field(description="The title of the dashboard")
    topic: Topic = api_field(description="Topic area the dashboard covers")
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

    @classmethod
    def from_dashboard_metadata_object(cls, obj: DashboardMetadataObject) -> "DashboardMetadata":
        return cls(
            name=obj.name,
            owner=obj.owner,
            is_built_in=obj.is_built_in,
            is_editable=obj.is_editable,
            layout_type=obj.layout_type,
            display=DashboardDisplay(
                title=obj.display.title,
                topic=Topic(
                    name=obj.display.topic.name,
                    breadcrumb=[
                        BreadcrumbItem(title=item.title, link=item.link)
                        for item in obj.display.topic.breadcrumb
                    ],
                ),
                hidden=obj.display.hidden,
                sort_index=obj.display.sort_index,
            ),
        )


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
