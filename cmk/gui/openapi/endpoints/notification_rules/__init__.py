#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Notification Rules

The notification rules endpoints give you the flexibility to create, edit, delete and show
all notification rules configured.

* POST for creating new notification rules.
* PUT for updating current notification rules.
* LIST for listing all current notification rules.
* GET for getting a single notification rule.
* DELETE for deleting a single notification rule.

"""

from collections.abc import Mapping
from typing import Any

from cmk.utils.notify_types import NotificationRuleID

from cmk.gui.config import active_config
from cmk.gui.http import Response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.notification_rules.request_schemas import NotificationRuleRequest
from cmk.gui.openapi.endpoints.notification_rules.response_schemas import (
    NotificationRuleResponse,
    NotificationRuleResponseCollection,
)
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.constructors import domain_object
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.openapi.utils import ProblemException, serve_json
from cmk.gui.rest_api_types.notifications_rule_types import APINotificationRule
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.notifications import (
    BulkNotAllowedException,
    NotificationRule,
    NotificationRuleConfigFile,
)

from cmk import fields

RO_PERMISSIONS = permissions.Perm("general.edit_notifications")
RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.see_all_folders"),
        RO_PERMISSIONS,
    ]
)


RULE_ID = {
    "rule_id": fields.String(
        required=True,
        description="The notification rule ID.",
        example="5425d554-5741-4bbf-b907-1a391dfab5bb",
    )
}


def _create_or_update_rule(
    incoming_rule_config: APINotificationRule,
    rule_id: NotificationRuleID | None,
    pprint_value: bool,
) -> Response:
    all_rules: NotificationRules = get_notification_rules()
    rule_from_request = NotificationRule.from_api_request(incoming_rule_config)
    if rule_id is not None:
        if rule_id not in all_rules:
            raise ProblemException(
                status=404,
                title=_("Not found"),
                detail=_("The rule_id %s does not exist.") % rule_id,
            )
        rule_from_request.rule_id = rule_id

    try:
        all_rules[rule_from_request.rule_id] = rule_from_request
        NotificationRuleConfigFile().save(
            [
                rule.to_mk_file_format(pprint_value=active_config.wato_pprint_config)
                for rule in all_rules.values()
            ],
            pprint_value=active_config.wato_pprint_config,
        )
    except BulkNotAllowedException as exc:
        raise ProblemException(
            status=400,
            title=_("Bulking not allowed"),
            detail=str(exc),
        )
    return serve_json(data=_serialize_notification_rule(rule_from_request), status=200)


NotificationRules = dict[NotificationRuleID, NotificationRule]


def get_notification_rules() -> NotificationRules:
    all_rules: list[NotificationRule] = [
        NotificationRule.from_mk_file_format(config)
        for config in NotificationRuleConfigFile().load_for_reading()
    ]
    notification_rules = NotificationRules({rule.rule_id: rule for rule in all_rules})
    return notification_rules


@Endpoint(
    constructors.object_href("notification_rule", "{rule_id}"),
    "cmk/show",
    method="get",
    tag_group="Setup",
    path_params=[RULE_ID],
    response_schema=NotificationRuleResponse,
    permissions_required=RO_PERMISSIONS,
)
def show_rule(params: Mapping[str, Any]) -> Response:
    """Show a notification rule"""
    user.need_permission("general.edit_notifications")
    all_rules = get_notification_rules()
    if rule := all_rules.get(NotificationRuleID(params["rule_id"])):
        return serve_json(_serialize_notification_rule(rule))
    raise ProblemException(
        status=404,
        title=_("The requested notification rule was not found"),
        detail=_("The rule_id %s does not exist.") % params["rule_id"],
    )


@Endpoint(
    constructors.collection_href("notification_rule"),
    ".../collection",
    method="get",
    tag_group="Setup",
    response_schema=NotificationRuleResponseCollection,
    permissions_required=RO_PERMISSIONS,
)
def show_rules(params: Mapping[str, Any]) -> Response:
    """Show all notification rules"""
    user.need_permission("general.edit_notifications")
    return serve_json(
        constructors.collection_object(
            domain_type="notification_rule",
            value=[
                _serialize_notification_rule(rule) for rule in get_notification_rules().values()
            ],
        )
    )


@Endpoint(
    constructors.collection_href("notification_rule"),
    "cmk/create",
    method="post",
    tag_group="Setup",
    request_schema=NotificationRuleRequest,
    response_schema=NotificationRuleResponse,
    permissions_required=RW_PERMISSIONS,
)
def post_rule(params: Mapping[str, Any]) -> Response:
    """Create a notification rule"""
    user.need_permission("wato.edit")
    user.need_permission("wato.see_all_folders")
    user.need_permission("general.edit_notifications")

    incoming_rule: APINotificationRule = params["body"]["rule_config"]
    return _create_or_update_rule(
        incoming_rule_config=incoming_rule,
        rule_id=None,
        pprint_value=active_config.wato_pprint_config,
    )


@Endpoint(
    constructors.object_href("notification_rule", "{rule_id}"),
    "cmk/update",
    method="put",
    tag_group="Setup",
    path_params=[RULE_ID],
    request_schema=NotificationRuleRequest,
    response_schema=NotificationRuleResponse,
    permissions_required=RW_PERMISSIONS,
)
def put_rule(params: Mapping[str, Any]) -> Response:
    """Update a notification rule"""
    user.need_permission("wato.edit")
    user.need_permission("wato.see_all_folders")
    user.need_permission("general.edit_notifications")
    incoming_rule: APINotificationRule = params["body"]["rule_config"]
    return _create_or_update_rule(
        incoming_rule_config=incoming_rule,
        rule_id=NotificationRuleID(params["rule_id"]),
        pprint_value=active_config.wato_pprint_config,
    )


@Endpoint(
    constructors.object_action_href("notification_rule", "{rule_id}", "delete"),
    ".../delete",
    method="post",
    tag_group="Setup",
    path_params=[RULE_ID],
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
)
def delete_rule(params: Mapping[str, Any]) -> Response:
    """Delete a notification rule"""
    user.need_permission("wato.edit")
    user.need_permission("wato.see_all_folders")
    user.need_permission("general.edit_notifications")

    rule_id = NotificationRuleID(params["rule_id"])
    all_rules: NotificationRules = get_notification_rules()
    if rule_id in all_rules:
        del all_rules[rule_id]
        updated_rules = [
            rule.to_mk_file_format(pprint_value=active_config.wato_pprint_config)
            for rule in all_rules.values()
        ]
        NotificationRuleConfigFile().save(
            updated_rules, pprint_value=active_config.wato_pprint_config
        )

    return Response(status=204)


def _serialize_notification_rule(rule: NotificationRule) -> DomainObject:
    return domain_object(
        domain_type="notification_rule",
        identifier=str(rule.rule_id),
        title=rule.rule_properties.description,
        extensions={"rule_config": rule.api_response()},
        editable=True,
        deletable=True,
    )


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(show_rule, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show_rules, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(post_rule, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(put_rule, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete_rule, ignore_duplicates=ignore_duplicates)
