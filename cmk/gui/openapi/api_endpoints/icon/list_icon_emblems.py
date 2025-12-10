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
from cmk.gui.theme.current_theme import theme
from cmk.gui.watolib.icons import (
    all_available_icon_emblem_data,
)


@api_model
class IconEmblemExtensions:
    is_built_in: bool = api_field(description="Whether this icon emblem is a built-in icon emblem.")
    category: str = api_field(description="The category of the icon emblem.")
    path: str = api_field(description="The path to the icon emblem.")


@api_model
class IconEmblemModel(DomainObjectModel):
    domainType: Literal["icon_emblem"] = api_field(description="The domain type of the object.")
    extensions: IconEmblemExtensions = api_field(
        description="All the metadata of this icon emblem."
    )


@api_model
class IconEmblemCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["icon_emblem"] = api_field(
        description="The domain type of the objects in the collection",
        example="icon_emblem",
    )
    # TODO: add proper example
    value: list[IconEmblemModel] = api_field(description="A list of icon emblems", example="")


def list_icon_emblems_v1(api_context: ApiContext) -> IconEmblemCollectionModel:
    """Show all icon emblems."""
    return IconEmblemCollectionModel(
        domainType="icon_emblem",
        id="all",
        links=[],
        value=[
            IconEmblemModel(
                domainType="icon_emblem",
                id=emblem.id,
                title=emblem.id,
                links=[],
                extensions=IconEmblemExtensions(
                    is_built_in=emblem.is_built_in,
                    category=emblem.category_id,
                    path=str(emblem.path),
                ),
            )
            for emblem in all_available_icon_emblem_data(
                theme, wato_icon_categories=api_context.config.wato_icon_categories
            )
        ],
    )


ENDPOINT_LIST_ICON_EMBLEMS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("icon_emblem"),
        link_relation="cmk/list_icon_emblems",
        method="get",
    ),
    permissions=EndpointPermissions(required=None),
    doc=EndpointDoc(family=ICON_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_icon_emblems_v1)},
)
