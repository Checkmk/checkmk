#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from typing import Annotated, Literal

import cmk.web.utils.permission_verification as permissions
from cmk.gui import visuals
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
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    TitledDomainObjectModel,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.type_defs import AnnotatedUserId, ViewName, ViewSpec, VisualContext
from cmk.gui.views.store import get_all_views, get_permitted_views

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
    filters: VisualContext = api_field(
        description="Active filters in the format filter_id -> (variable -> value)"
    )
    is_mobile: bool = api_field(description='Whether the view option "mobile" is set or not.')
    owner: AnnotatedUserId = api_field(
        description="Owner of the view, an empty string for a built-in one."
    )


@api_model
class ViewModel(TitledDomainObjectModel):
    domainType: Literal["view"] = api_field(description="The domain type of the object.")
    extensions: ViewExtensions = api_field(description="Parts of the configuration of this view.")


@api_model
class ViewCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["view"] = api_field(
        description="The domain type of the objects in the collection"
    )
    value: list[ViewModel] = api_field(description="A list of views.")


def list_views_v1(
    api_context: ApiContext,
    all_owners: Annotated[
        bool,
        QueryParam(
            description=(
                "List every copy of a view the user may open, one per owner, instead of the one "
                "copy each view name resolves to. Several entries then share an ID."
            ),
            example="False",
        ),
    ] = False,
) -> ViewCollectionModel:
    """List views."""
    specs: Iterable[tuple[ViewName, ViewSpec]]
    if all_owners:
        specs = (
            (view_name, view_spec)
            for view_name, copies in visuals.available_by_owner(
                "views", get_all_views(), api_context.config.user_permissions()
            ).items()
            for view_spec in copies.values()
        )
    else:
        specs = get_permitted_views().items()
    return ViewCollectionModel(
        id="all",
        domainType="view",
        links=[],
        value=[_view_model(view_name, view_spec) for view_name, view_spec in specs],
    )


def _view_model(view_name: ViewName, view_spec: ViewSpec) -> ViewModel:
    return ViewModel(
        id=view_name,
        domainType="view",
        title=str(view_spec.get("title", view_name)),  # convert lazy string
        extensions=ViewExtensions(
            data_source=view_spec["datasource"],
            restricted_to_single=list(view_spec["single_infos"]),
            filters=view_spec.get("context", {}),
            is_mobile=view_spec.get("mobile", False),
            owner=view_spec["owner"],
        ),
        links=[],
    )


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
