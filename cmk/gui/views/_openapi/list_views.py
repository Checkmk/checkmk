#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal

import cmk.gui.utils.permission_verification as permissions
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

from ..store import get_permitted_views
from ._family import VIEW_FAMILY


@api_model
class ViewExtensions:
    # NOTE: intentionally sparse, so far this is only used in the dashboards UI
    data_source: str = api_field(description="ID of the data source.")
    restricted_to_single: list[str] = api_field(
        description=(
            "A list of single infos that this view is restricted to. "
            "This means that the view must be filtered to exactly one item for each info name."
        )
    )


@api_model
class ViewModel(DomainObjectModel):
    domainType: Literal["view"] = api_field(description="The domain type of the object.")
    extensions: ViewExtensions = api_field(description="Parts of the configuration of this view.")


@api_model
class ViewCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["view"] = api_field(
        description="The domain type of the objects in the collection"
    )
    value: list[ViewModel] = api_field(description="A list of views.")


def list_views_v1() -> ViewCollectionModel:
    """List views."""
    views = []
    for view_name, view_spec in get_permitted_views().items():
        dashboard_model = ViewModel(
            id=view_name,
            domainType="view",
            title=str(view_spec.get("title", view_name)),  # convert lazy string
            extensions=ViewExtensions(
                data_source=view_spec["datasource"],
                restricted_to_single=list(view_spec["single_infos"]),
            ),
            links=[],
        )
        views.append(dashboard_model)

    return ViewCollectionModel(id="all", domainType="view", links=[], value=views)


ENDPOINT_LIST_VIEWS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("view"),
        link_relation="cmk/list",
        method="get",
    ),
    permissions=EndpointPermissions(
        required=permissions.AllPerm(
            [
                permissions.Perm("general.edit_views"),  # always required, even for reads
                # optional permissions to allow access to more views the user doesn't own
                permissions.Optional(permissions.Perm("general.see_user_views")),
                permissions.Optional(permissions.Perm("general.see_packaged_views")),
                # every view has its own permissions, all of which might be checked (and are optional)
                permissions.PrefixPerm("view"),
            ]
        )
    ),
    doc=EndpointDoc(family=VIEW_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_views_v1)},
)
