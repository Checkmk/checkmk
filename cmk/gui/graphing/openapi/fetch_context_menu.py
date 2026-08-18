#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.gui.graphing.openapi.utils import serialize_menu_dropdown
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
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.visuals import page_menu_dropdown_add_to_visual
from cmk.web.utils import permission_verification as permissions

from ._family import GRAPH_FAMILY
from .models import BurgerMenuCollection


def fetch_context_menu_v1(
    api_context: ApiContext,
    add_type: Annotated[
        str,
        QueryParam(
            description="The type of element the context menu is opened for.",
            example="pnpgraph",
        ),
    ],
) -> BurgerMenuCollection:
    """Fetch the context menu entries for a graph"""

    user_permissions = api_context.config.user_permissions()

    menu_dropdown = page_menu_dropdown_add_to_visual(
        add_type=add_type,
        name="",
        user_permissions=user_permissions,
    )[0]

    return BurgerMenuCollection(
        id="burger_menu",
        domainType="burger_menu",
        value=serialize_menu_dropdown(menu_dropdown),
        links=[],
    )


ENDPOINT_FETCH_CONTEXT_MENU = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("graph", "fetch_context_menu"),
        link_relation=".../fetch",
        method="get",
    ),
    permissions=EndpointPermissions(
        # Assembling the menu asks every visual type and container page type whether the user may
        # edit it, so which permissions get checked depends on what is registered.
        required=permissions.DynamicRuntimePerm(
            description=(
                "Checks the edit permission of every visual type and container page type that "
                "could hold the graph, e.g. general.edit_dashboards."
            )
        )
    ),
    doc=EndpointDoc(family=GRAPH_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=fetch_context_menu_v1)},
)
