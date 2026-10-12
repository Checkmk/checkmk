#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from typing import Literal

import cmk.web.utils.permission_verification as permissions
from cmk.ccc.version import Edition
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.restful_objects.type_defs import LinkRelation

from ._family import DASHBOARD_FAMILY
from ._widget_resolution import PERMISSIONS_LINK_TARGET, PERMISSIONS_WIDGET_QUERY
from .model.response_model import ComputedWidgetResponse

type _ComputeHandler[T] = Callable[..., ComputedWidgetResponse[T]]  # type: ignore[explicit-any]


def widget_compute_endpoint[T](
    *,
    action: str,
    link_relation: LinkRelation,
    handler: _ComputeHandler[T],
    link_targets: bool,
    supported_editions: set[Edition] | Literal["all"],
    shared_dashboards: bool = True,
) -> VersionedEndpoint:
    """The endpoint that computes the data of a widget, for a dashboard token if shared."""
    return VersionedEndpoint(
        metadata=EndpointMetadata(
            path=domain_type_action_href(domain_type="dashboard", action=action),
            link_relation=link_relation,
            method="post",
        ),
        permissions=EndpointPermissions(
            required=permissions.AllPerm([PERMISSIONS_WIDGET_QUERY, PERMISSIONS_LINK_TARGET])
            if link_targets
            else PERMISSIONS_WIDGET_QUERY
        ),
        doc=EndpointDoc(
            family=DASHBOARD_FAMILY.name,
            supported_editions=set() if supported_editions == "all" else supported_editions,
        ),
        behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
        versions={APIVersion.INTERNAL: EndpointHandler(handler=handler)},
        allowed_tokens={"dashboard"} if shared_dashboards else set(),
    )
