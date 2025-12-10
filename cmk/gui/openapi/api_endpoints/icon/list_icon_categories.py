#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from typing import Literal

from cmk.gui.openapi.api_endpoints.icon._family import ICON_FAMILY
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
from cmk.gui.watolib.icons import all_icon_categories


@api_model
class IconCategoryModel(DomainObjectModel):
    domainType: Literal["icon_category"] = api_field(description="The domain type of the object.")


@api_model
class IconCategoryCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["icon_category"] = api_field(
        description="The domain type of the objects in the collection",
        example="icon_category",
    )
    value: list[IconCategoryModel] = api_field(
        description="A list of icon emblems",
        example=[
            {
                "domainType": "icon_category",
                "id": "example_category",
                "title": "Example Category",
                "links": [],
            }
        ],
    )


def list_icon_categories_v1(api_context: ApiContext) -> IconCategoryCollectionModel:
    """Show all icon categories."""
    return IconCategoryCollectionModel(
        domainType="icon_category",
        id="all",
        links=[],
        value=[
            IconCategoryModel(
                domainType="icon_category",
                id=category_id,
                title=category_alias,
                links=[],
            )
            for category_id, category_alias in all_icon_categories(
                api_context.config.wato_icon_categories
            )
        ],
    )


ENDPOINT_LIST_ICON_CATEGORIES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("icon_category"),
        link_relation="cmk/list_icon_categories",
        method="get",
    ),
    permissions=EndpointPermissions(required=None),
    doc=EndpointDoc(family=ICON_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_icon_categories_v1)},
)
