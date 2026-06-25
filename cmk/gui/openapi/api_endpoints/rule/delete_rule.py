#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_quick_setup
from cmk.gui.watolib.rulesets import AllRulesets, visible_rulesets

from ._family import RULE_FAMILY
from ._utils import make_pending_changes, RW_PERMISSIONS


def delete_rule_v1(
    api_context: ApiContext,
    rule_id: Annotated[
        str,
        PathParam(
            description="The ID of the rule.", example="0a168697-14a2-48d0-9c3c-ca65569a39e2"
        ),
    ],
) -> ApiResponse[None]:
    """Delete a rule"""
    user.need_permission("wato.edit")
    user.need_permission("wato.rulesets")

    all_rulesets = AllRulesets.load_all_rulesets()
    for ruleset in visible_rulesets(all_rulesets.get_rulesets()).values():
        for _folder, _index, rule in ruleset.get_rules():
            if rule.id == rule_id:
                if is_locked_by_quick_setup(rule.locked_by):
                    raise ProblemException(
                        status=400,
                        title="Rule is managed by Quick setup",
                        detail="Rules managed by Quick setup cannot be deleted.",
                    )
                ruleset.delete_rule(
                    rule, create_change=True, pending_changes=make_pending_changes(api_context)
                )
                all_rulesets.save(
                    pprint_value=api_context.config.wato_pprint_config,
                    debug=api_context.config.debug,
                )
                return ApiResponse(body=None, status_code=204)

    raise ProblemException(
        status=404,
        title="Rule not found.",
        detail=f"The rule with ID {rule_id!r} could not be found.",
    )


ENDPOINT_DELETE_RULE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("rule", "{rule_id}"),
        link_relation=".../delete",
        method="delete",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=RULE_FAMILY.name),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=delete_rule_v1,
            additional_status_codes=[400, 404],
            status_descriptions={
                204: "Rule was deleted successfully.",
                400: "The rule is locked and cannot be deleted.",
                404: "The rule to be deleted was not found.",
            },
        )
    },
)
