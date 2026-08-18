#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.graphing.openapi._add_to import AddableGraph
from cmk.gui.graphing.openapi._family import GRAPH_FAMILY
from cmk.gui.graphing.openapi.models import AddToContainerRequest, AddToContainerResponse
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.pagetypes import all_page_types, OverridableContainer
from cmk.web.utils import permission_verification as permissions


def _container_names() -> str:
    return ", ".join(
        sorted(
            name
            for name, page_type in all_page_types().items()
            if issubclass(page_type, OverridableContainer)
        )
    )


def add_to_container_v1(
    api_context: ApiContext, body: AddToContainerRequest
) -> AddToContainerResponse:
    """Add a graph to a container"""
    addable = AddableGraph.parse(body.specification, body.internal)
    page_type = all_page_types().get(body.family)
    if page_type is None or not issubclass(page_type, OverridableContainer):
        raise ProblemException(
            status=400,
            title="Unknown container type",
            detail=(
                f"There is no container page type '{body.family}'. "
                f"Known types: {_container_names()}."
            ),
        )

    try:
        # The target page is always None here; only the sidebar hint carries information.
        _target_page, sidebar_reload_required = page_type.add_element_via_popup(
            body.id,
            addable.add_type,
            {"context": None, "parameters": addable.parameters()},
            api_context.config.user_permissions(),
            active_config,
        )
    except MKAuthException as exc:
        raise ProblemException(
            status=403,
            title="Not allowed to add to this container",
            detail=str(exc),
        ) from exc
    except MKGeneralException as exc:
        raise ProblemException(
            status=404,
            title="Container not found",
            detail=str(exc),
        ) from exc

    return AddToContainerResponse(sidebar_reload_required=sidebar_reload_required)


ENDPOINT_ADD_TO_CONTAINER = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("graph", "add_to_container"),
        link_relation=".../add-to",
        method="post",
    ),
    permissions=EndpointPermissions(
        # Which permission applies depends on the container page type the caller targets.
        required=permissions.DynamicRuntimePerm(
            description=(
                "Requires the edit permission of the targeted container page type, e.g. "
                "general.edit_graph_collection for a graph collection."
            )
        )
    ),
    doc=EndpointDoc(family=GRAPH_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=add_to_container_v1)},
)
