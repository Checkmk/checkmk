#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.utils.misc import gen_id
from cmk.gui.watolib.rulesets import FolderRulesets

from ._family import RULE_FAMILY
from ._utils import (
    create_rule_object,
    get_rule_by_id,
    make_pending_changes,
    retrieve_from_rulesets,
    rule_etag,
    RW_PERMISSIONS,
    serialize_rule,
    validate_value,
)
from .models.request_models import CreateRuleModel
from .models.response_models import RuleObjectModel


def create_rule_v1(api_context: ApiContext, body: CreateRuleModel) -> ApiResponse[RuleObjectModel]:
    """Create rule"""
    user.need_permission("wato.edit")
    user.need_permission("wato.rulesets")

    folder = body.folder
    folder.permissions.need_permission("write", user)

    rulesets = FolderRulesets.load_folder_rulesets(folder)
    ruleset = retrieve_from_rulesets(rulesets, body.ruleset)

    validate_value(ruleset, body.value_raw)

    rule = create_rule_object(
        folder, ruleset, body.conditions, body.properties, body.value_raw, gen_id()
    )
    index = ruleset.append_rule(folder, rule)
    rulesets.save_folder(
        pprint_value=api_context.config.wato_pprint_config, debug=api_context.config.debug
    )
    ruleset.add_new_rule_change(
        index, folder, rule, pending_changes=make_pending_changes(api_context)
    )

    rule_entry = get_rule_by_id(rule.id)
    return ApiResponse(
        body=serialize_rule(rule_entry, api_context),
        status_code=200,
        etag=rule_etag(rule_entry.rule),
    )


ENDPOINT_CREATE_RULE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("rule"),
        link_relation="cmk/create",
        method="post",
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=RULE_FAMILY.name),
    behavior=EndpointBehavior(etag="output"),
    versions={APIVersion.V1: EndpointHandler(handler=create_rule_v1)},
)
