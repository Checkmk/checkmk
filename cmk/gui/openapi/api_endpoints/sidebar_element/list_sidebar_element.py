#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
    LinkModel,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.sidebar._snapin import all_snapins
from cmk.gui.utils import permission_verification as permissions

from .endpoint_family import SIDEBAR_ELEMENT_FAMILY


@api_model
class SidebarElementModel(DomainObjectModel):
    domainType: Literal["constant"] = api_field(description="The domain type of the object.")


@api_model
class SidebarElementModelCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["constant"] = api_field(
        description="The domain type of the objects in the collection"
    )
    value: list[SidebarElementModel] = api_field(
        description="The list of Sidebar Element objects", example=""
    )


def list_sidebar_element_v1(api_context: ApiContext) -> SidebarElementModelCollectionModel:
    """List all sidebar elements from snapins"""

    sidebar_elements = []
    snapins = all_snapins(api_context.config.user_permissions())
    for key, snapin in snapins.items():
        title = snapin.title()
        model = SidebarElementModel(
            id=key,
            domainType="constant",
            title=title,
            links=[],
        )

        sidebar_elements.append(model)

    return SidebarElementModelCollectionModel(
        id="sidebar_element",
        domainType="constant",
        value=sidebar_elements,
        links=[LinkModel.create("self", collection_href("sidebar_element"))],
    )


ENDPOINT_LIST_SIDEBAR_ELEMENT = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("sidebar_element"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(required=permissions.AllPerm([])),
    doc=EndpointDoc(family=SIDEBAR_ELEMENT_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=list_sidebar_element_v1)},
)
