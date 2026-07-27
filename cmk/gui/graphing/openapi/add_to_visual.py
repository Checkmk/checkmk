#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.graphing.openapi._add_to import AddableGraph
from cmk.gui.graphing.openapi._family import GRAPH_FAMILY
from cmk.gui.graphing.openapi.models import AddToRequest
from cmk.gui.http import request
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
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.visuals.type import visual_type_registry

# Views are a registered visual type but cannot hold a graph: their add_visual_handler is a no-op
# and they offer no add-to entries. Accepting them would report success while storing nothing.
_GRAPH_TARGET_VISUAL_TYPES = ("dashboards", "reports")


def add_to_visual_v1(api_context: ApiContext, body: AddToRequest) -> None:
    """Add a graph to a visual container"""
    addable = AddableGraph.parse(body.specification)
    if body.family not in _GRAPH_TARGET_VISUAL_TYPES:
        raise ProblemException(
            status=400,
            title="Cannot add a graph to this visual type",
            detail=(
                f"Graphs cannot be added to '{body.family}'. Supported visual types: "
                f"{', '.join(_GRAPH_TARGET_VISUAL_TYPES)}."
            ),
        )
    try:
        visual_type = visual_type_registry[body.family]()
    except KeyError:
        raise ProblemException(
            status=400,
            title="Unknown visual type",
            detail=(
                f"There is no visual type '{body.family}'. Known types: "
                f"{', '.join(sorted(visual_type_registry))}."
            ),
        )

    try:
        visual_type.add_visual_handler(
            request,
            body.id,
            addable.add_type,
            # The specification carries the context; the backends unpack it themselves.
            None,
            addable.parameters(),
            api_context.config.user_permissions(),
        )
    except MKAuthException as exc:
        raise ProblemException(
            status=403,
            title="Not allowed to add to this visual",
            detail=str(exc),
        ) from exc
    except (MKUserError, MKGeneralException) as exc:
        raise ProblemException(
            status=404,
            title="Visual not found",
            detail=str(exc),
        ) from exc


ENDPOINT_ADD_TO_VISUAL = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("graph", "add_to_visual"),
        link_relation=".../action-param",
        method="post",
        # No response model: add_visual_handler reports nothing back, unlike the container side.
        content_type=None,
    ),
    permissions=EndpointPermissions(
        # Which permission applies depends on the visual type the caller targets.
        required=permissions.DynamicRuntimePerm(
            description=(
                "Requires the edit permission of the targeted visual type, e.g. "
                "general.edit_dashboards for a dashboard."
            )
        )
    ),
    doc=EndpointDoc(family=GRAPH_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=add_to_visual_v1)},
)
