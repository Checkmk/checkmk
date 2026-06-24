#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_href

from ._family import RULE_FAMILY
from ._utils import get_rule_by_id, PERMISSIONS, rule_etag, serialize_rule
from .models.response_models import RuleObjectModel


def show_rule_v1(
    api_context: ApiContext,
    rule_id: Annotated[
        str,
        PathParam(
            description="The ID of the rule.", example="0a168697-14a2-48d0-9c3c-ca65569a39e2"
        ),
    ],
) -> ApiResponse[RuleObjectModel]:
    """Show a rule"""
    user.need_permission("wato.rulesets")
    rule_entry = get_rule_by_id(rule_id)
    return ApiResponse(
        body=serialize_rule(rule_entry, api_context),
        status_code=200,
        etag=rule_etag(rule_entry.rule),
    )


ENDPOINT_SHOW_RULE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("rule", "{rule_id}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=RULE_FAMILY.name),
    behavior=EndpointBehavior(etag="output"),
    versions={APIVersion.V1: EndpointHandler(handler=show_rule_v1)},
)
