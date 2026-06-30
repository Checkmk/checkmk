#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, assert_never

from pydantic import Discriminator

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
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.gui.openapi.utils import ProblemException, RestAPIRequestDataValidationException
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_quick_setup
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.rulesets import Ruleset

from ._family import RULE_FAMILY
from ._utils import (
    get_rule_by_id,
    make_pending_changes,
    RW_PERMISSIONS,
    serialize_rule,
    validate_rule_move,
)
from .models.request_models import MoveToFolderModel, MoveToSpecificRuleModel
from .models.response_models import RuleObjectModel


def move_rule_v1(
    api_context: ApiContext,
    body: Annotated[MoveToFolderModel | MoveToSpecificRuleModel, Discriminator("position")],
    rule_id: Annotated[
        str,
        PathParam(
            description="The ID of the rule.", example="0a168697-14a2-48d0-9c3c-ca65569a39e2"
        ),
    ],
) -> RuleObjectModel:
    """Move a rule to a specific location"""
    user.need_permission("wato.edit")
    user.need_permission("wato.rulesets")

    source_entry = get_rule_by_id(rule_id)

    if is_locked_by_quick_setup(source_entry.rule.locked_by):
        raise ProblemException(
            status=400,
            title="Rule is managed by Quick setup",
            detail="Rules managed by Quick setup cannot be moved.",
        )

    all_rulesets = source_entry.all_rulesets

    index: int
    dest_folder: Folder
    match body:
        case MoveToFolderModel():
            dest_folder = body.folder
            index = Ruleset.TOP if body.position == "top_of_folder" else Ruleset.BOTTOM
        case MoveToSpecificRuleModel():
            dest_entry = get_rule_by_id(body.rule_id, all_rulesets=all_rulesets)
            validate_rule_move(source_entry, dest_entry)
            if body.position == "before_specific_rule":
                if is_locked_by_quick_setup(dest_entry.rule.locked_by):
                    raise RestAPIRequestDataValidationException(
                        title="Invalid rule move.",
                        detail="Cannot move before a rule managed by Quick setup.",
                    )
                index = dest_entry.index_nr
                dest_folder = dest_entry.folder
            else:  # after_specific_rule
                dest_folder = dest_entry.folder
                index = dest_entry.index_nr + 1
                actual_index = source_entry.ruleset.get_index_for_move(
                    source_entry.folder, source_entry.rule, index
                )
                if index != actual_index:
                    raise RestAPIRequestDataValidationException(
                        title="Invalid rule move.",
                        detail="Cannot move before a rule managed by Quick setup.",
                    )
        case _:
            assert_never(body)

    dest_folder.permissions.need_permission("write", user)
    source_entry.ruleset.move_to_folder(
        source_entry.rule, dest_folder, index, pending_changes=make_pending_changes(api_context)
    )
    all_rulesets.save(
        pprint_value=api_context.config.wato_pprint_config, debug=api_context.config.debug
    )

    return serialize_rule(get_rule_by_id(rule_id), api_context)


ENDPOINT_MOVE_RULE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("rule", "{rule_id}", "move"),
        link_relation="cmk/move",
        method="post",
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=RULE_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=move_rule_v1)},
)
