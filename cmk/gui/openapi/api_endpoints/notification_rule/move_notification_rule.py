#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, assert_never

from pydantic import Discriminator

from cmk.events.notify_types import NotificationRuleID
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
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.gui.openapi.shared_endpoint_families.notification_rules import NOTIFICATION_RULES_FAMILY
from cmk.gui.openapi.utils import RestAPIRequestDataValidationException
from cmk.gui.watolib.notifications import NotificationRuleConfigFile

from .models.request_models import (
    MoveNotificationRuleToListPositionModel,
    MoveNotificationRuleToSpecificRuleModel,
)
from .utils import index_of_notification_rule, make_pending_changes, RW_PERMISSIONS


def move_notification_rule_v1(
    api_context: ApiContext,
    body: Annotated[
        MoveNotificationRuleToListPositionModel | MoveNotificationRuleToSpecificRuleModel,
        Discriminator("position"),
    ],
    rule_id: Annotated[
        str,
        PathParam(
            description="The notification rule ID.",
            example="5425d554-5741-4bbf-b907-1a391dfab5bb",
        ),
    ],
) -> ApiResponse[None]:
    """Move a notification rule to a different position

    Notification rules are evaluated from top to bottom, so their position decides which rule
    matches first. Read the rule again to see its new `rule_index`.
    """
    user.need_permission("wato.edit")
    user.need_permission("wato.see_all_folders")
    user.need_permission("general.edit_notifications")

    config_file = NotificationRuleConfigFile()
    rules = config_file.load_for_modification()
    source_index = index_of_notification_rule(rules, NotificationRuleID(rule_id))
    rule = rules.pop(source_index)

    target_index: int
    match body:
        case MoveNotificationRuleToListPositionModel():
            target_index = 0 if body.position == "top_of_list" else len(rules)
        case MoveNotificationRuleToSpecificRuleModel():
            if body.rule_id == rule_id:
                raise RestAPIRequestDataValidationException(
                    title="Invalid notification rule move.",
                    detail="You cannot move a rule before/after itself.",
                )
            destination_index = index_of_notification_rule(rules, NotificationRuleID(body.rule_id))
            target_index = (
                destination_index
                if body.position == "before_specific_rule"
                else destination_index + 1
            )
        case _:
            assert_never(body)

    rules.insert(target_index, rule)
    config_file.rule_moved(
        rules=rules,
        rule_number=str(source_index),
        pprint_value=api_context.config.wato_pprint_config,
        pending_changes=make_pending_changes(api_context),
    )
    return ApiResponse(body=None, status_code=204)


ENDPOINT_MOVE_NOTIFICATION_RULE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("notification_rule", "{rule_id}", "move"),
        link_relation="cmk/move",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=NOTIFICATION_RULES_FAMILY.name),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=move_notification_rule_v1,
            status_descriptions={204: "The notification rule was moved."},
        )
    },
)
