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
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_quick_setup

from ._family import RULE_FAMILY
from ._utils import (
    create_rule_object,
    get_rule_by_id,
    make_pending_changes,
    rule_etag,
    RW_PERMISSIONS,
    serialize_rule,
    validate_value,
)
from .models.request_models import UpdateRuleModel
from .models.response_models import RuleObjectModel


def edit_rule_v1(
    api_context: ApiContext,
    body: UpdateRuleModel,
    rule_id: Annotated[
        str,
        PathParam(
            description="The ID of the rule.", example="0a168697-14a2-48d0-9c3c-ca65569a39e2"
        ),
    ],
) -> ApiResponse[RuleObjectModel]:
    """Modify a rule"""
    user.need_permission("wato.edit")
    user.need_permission("wato.rulesets")

    rule_entry = get_rule_by_id(rule_id)
    if api_context.etag.enabled:
        api_context.etag.verify(rule_etag(rule_entry.rule))

    folder = rule_entry.folder
    folder.permissions.need_permission("write")

    ruleset = rule_entry.ruleset
    rulesets = rule_entry.all_rulesets
    current_rule = rule_entry.rule

    validate_value(ruleset, body.value_raw)

    new_rule = create_rule_object(
        folder, ruleset, body.conditions, body.properties, body.value_raw, rule_id
    )

    if (
        is_locked_by_quick_setup(rule_entry.rule.locked_by)
        and rule_entry.rule.conditions != new_rule.conditions
    ):
        raise ProblemException(
            status=400,
            title="Rule is managed by Quick setup",
            detail="Conditions cannot be modified for rules managed by Quick setup.",
        )

    ruleset.edit_rule(current_rule, new_rule, pending_changes=make_pending_changes(api_context))
    rulesets.save_folder(
        folder, pprint_value=api_context.config.wato_pprint_config, debug=api_context.config.debug
    )

    new_rule_entry = get_rule_by_id(rule_id)
    return ApiResponse(
        body=serialize_rule(new_rule_entry, api_context),
        status_code=200,
        etag=rule_etag(new_rule_entry.rule),
    )


ENDPOINT_EDIT_RULE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("rule", "{rule_id}"),
        link_relation=".../update",
        method="put",
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=RULE_FAMILY.name),
    behavior=EndpointBehavior(etag="both"),
    versions={APIVersion.V1: EndpointHandler(handler=edit_rule_v1)},
)
