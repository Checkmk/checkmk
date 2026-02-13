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
from cmk.gui.theme import make_theme
from cmk.gui.userdb import load_custom_attr
from cmk.gui.watolib.icons import all_available_icon_data


@api_model
class IconExtensions:
    is_built_in: bool = api_field(description="Whether this icon is a built-in icon.")
    category: str = api_field(description="The category of the icon.")
    path: str = api_field(description="The path to the icon.")


@api_model
class IconModel(DomainObjectModel):
    domainType: Literal["icon"] = api_field(description="The domain type of the object.")
    extensions: IconExtensions = api_field(description="All the metadata of this icon.")


@api_model
class IconCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["icon"] = api_field(
        description="The domain type of the objects in the collection",
        example="icon",
    )
    # TODO: add proper example
    value: list[IconModel] = api_field(description="A list of icons", example="")


def list_icons_v1(api_context: ApiContext) -> IconCollectionModel:
    """Show all icons."""
    theme = make_theme(validate_choices=False)
    theme.from_config(api_context.config.ui_theme)
    if user_id := api_context.user_id:
        theme.set(load_custom_attr(user_id=user_id, key="ui_theme", parser=str))
    return IconCollectionModel(
        domainType="icon",
        id="all",
        links=[],
        value=[
            IconModel(
                domainType="icon",
                id=icon.id,
                title=icon.id,
                links=[],
                extensions=IconExtensions(
                    is_built_in=icon.is_built_in,
                    category=icon.category_id,
                    path=str(icon.path),
                ),
            )
            for icon in all_available_icon_data(
                theme, wato_icon_categories=api_context.config.wato_icon_categories
            )
        ],
    )


ENDPOINT_LIST_ICONS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("icon"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(required=None),
    doc=EndpointDoc(family=ICON_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_icons_v1)},
)
