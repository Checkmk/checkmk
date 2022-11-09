#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Business intelligence (BI)

BI is used in Checkmk to set up a tree based on the status of hosts and services as branches and to
extend with higher level nodes summarizing (or aggregating) the status of the contained objects.
A BI pack contains the configuration data by means of BI aggregations and BI rules.
A BI aggregation is a tree of nodes and a BI rule is used to define a node and its status.

You can find an introduction to BI in the
[Checkmk guide](https://docs.checkmk.com/latest/en/bi.html).
"""

import http
import http.client

from cmk.utils.bi.bi_aggregation import BIAggregation, BIAggregationSchema
from cmk.utils.bi.bi_lib import ReqBoolean, ReqList, ReqString
from cmk.utils.bi.bi_packs import (
    AggregationNotFoundException,
    BIAggregationPack,
    DeleteErrorUsedByAggregation,
    DeleteErrorUsedByRule,
    RuleNotFoundException,
)
from cmk.utils.bi.bi_rule import BIRule, BIRuleSchema
from cmk.utils.bi.bi_schema import Schema
from cmk.utils.exceptions import MKGeneralException

from cmk.gui import fields as gui_fields
from cmk.gui.bi import api_get_aggregation_state, get_cached_bi_packs
from cmk.gui.globals import user
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    permissions,
    response_schemas,
)
from cmk.gui.plugins.openapi.utils import ProblemException, serve_json

from cmk import fields

BI_RULE_ID = {
    "rule_id": fields.String(
        description="The unique id for the rule",
        example="rule1",
    ),
}
BI_AGGR_ID = {
    "aggregation_id": fields.String(
        description="The unique id for the aggregation",
        example="aggregation1",
    ),
}
BI_PACK_ID = {
    "pack_id": fields.String(
        description="The unique id for the aggregation pack",
        example="pack1",
    ),
}


def _bailout_with_message(message):
    raise ProblemException(404, http.client.responses[404], message)


#   .--Rules---------------------------------------------------------------.
#   |                       ____        _                                  |
#   |                      |  _ \ _   _| | ___  ___                        |
#   |                      | |_) | | | | |/ _ \/ __|                       |
#   |                      |  _ <| |_| | |  __/\__ \                       |
#   |                      |_| \_\\__,_|_|\___||___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class BIRuleEndpointSchema(BIRuleSchema):
    pack_id = ReqString(
        dump_default="",
        example="pack1",
        description="TODO: Hier muß Andreas noch etwas reinschreiben!",
    )


RO_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.bi_rules"),
        permissions.Ignore(
            permissions.AnyPerm(
                [
                    permissions.Perm("bi.see_all"),
                    permissions.Perm("general.see_all"),
                    permissions.Perm("mkeventd.seeall"),
                ]
            )
        ),
    ]
)

RW_BI_RULES_PERMISSION = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.bi_rules"),
    ]
)

RW_BI_ADMIN_PERMISSIONS = permissions.AllPerm(
    [
        *RW_BI_RULES_PERMISSION.perms,
        permissions.Perm("wato.bi_admin"),
    ]
)


@Endpoint(
    constructors.object_href("bi_rule", "{rule_id}"),
    "cmk/get_bi_rule",
    method="get",
    path_params=[BI_RULE_ID],
    convert_response=False,
    response_schema=BIRuleEndpointSchema,
    permissions_required=RO_PERMISSIONS,
)
def get_bi_rule(params):
    """Show a BI rule"""
    user.need_permission("wato.bi_rules")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    try:
        bi_rule = bi_packs.get_rule_mandatory(params["rule_id"])
    except RuleNotFoundException:
        _bailout_with_message("Unknown bi_rule: %s" % params["rule_id"])

    data = {"pack_id": bi_rule.pack_id}
    data.update(BIRuleSchema().dump(bi_rule))
    return serve_json(data)


@Endpoint(
    constructors.object_href("bi_rule", "{rule_id}"),
    "cmk/put_bi_rule",
    method="put",
    path_params=[BI_RULE_ID],
    convert_response=False,
    request_schema=BIRuleEndpointSchema,
    response_schema=BIRuleEndpointSchema,
    permissions_required=RW_BI_RULES_PERMISSION,
)
def put_bi_rule(params):
    """Update an existing BI rule"""
    return _update_bi_rule(params, must_exist=True)


@Endpoint(
    constructors.object_href("bi_rule", "{rule_id}"),
    "cmk/post_bi_rule",
    method="post",
    path_params=[BI_RULE_ID],
    convert_response=False,
    request_schema=BIRuleEndpointSchema,
    response_schema=BIRuleEndpointSchema,
    permissions_required=RW_BI_RULES_PERMISSION,
)
def post_bi_rule(params):
    """Create a new BI rule"""
    return _update_bi_rule(params, must_exist=False)


def _update_bi_rule(params, must_exist: bool):
    user.need_permission("wato.edit")
    user.need_permission("wato.bi_rules")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    rule_config = params["body"]
    try:
        target_pack = bi_packs.get_pack_mandatory(rule_config["pack_id"])
    except KeyError:
        _bailout_with_message("Unknown bi_pack: %s" % rule_config["pack_id"])

    rule_id = params["rule_id"]
    rule_exists = bool(bi_packs.get_rule(rule_id))
    if rule_exists and not must_exist:
        _bailout_with_message("This rule_id already exists: %s" % rule_id)
    if not rule_exists and must_exist:
        _bailout_with_message("This rule_id does not exist: %s" % rule_id)

    rule_config["id"] = rule_id
    bi_rule = BIRule(rule_config)
    target_pack.add_rule(bi_rule)
    bi_packs.save_config()

    data = {"pack_id": bi_rule.pack_id}
    data.update(bi_rule.schema()().dump(bi_rule))
    return serve_json(data)


@Endpoint(
    constructors.object_href("bi_rule", "{rule_id}"),
    "cmk/delete_bi_rule",
    method="delete",
    path_params=[BI_RULE_ID],
    convert_response=False,
    output_empty=True,
    permissions_required=RW_BI_RULES_PERMISSION,
    additional_status_codes=[409],
)
def delete_bi_rule(params):
    """Delete BI rule"""
    user.need_permission("wato.edit")
    user.need_permission("wato.bi_rules")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    try:
        bi_rule = bi_packs.get_rule_mandatory(params["rule_id"])
    except RuleNotFoundException:
        _bailout_with_message("Unknown bi_rule: %s" % params["rule_id"])

    try:
        bi_packs.delete_rule(bi_rule.id)
    except (DeleteErrorUsedByRule, DeleteErrorUsedByAggregation) as e:
        raise ProblemException(status=409, title=http.client.responses[409], detail=e.args[0])
    bi_packs.save_config()
    return Response(status=204)


#   .--Aggregations--------------------------------------------------------.
#   |       _                                    _   _                     |
#   |      / \   __ _  __ _ _ __ ___  __ _  __ _| |_(_) ___  _ __  ___     |
#   |     / _ \ / _` |/ _` | '__/ _ \/ _` |/ _` | __| |/ _ \| '_ \/ __|    |
#   |    / ___ \ (_| | (_| | | |  __/ (_| | (_| | |_| | (_) | | | \__ \    |
#   |   /_/   \_\__, |\__, |_|  \___|\__, |\__,_|\__|_|\___/|_| |_|___/    |
#   |           |___/ |___/          |___/                                 |
#   +----------------------------------------------------------------------+


class BIAggregationEndpointSchema(BIAggregationSchema):
    pack_id = ReqString(
        dump_default="",
        example="pack1",
        description="TODO: Hier muß Andreas noch etwas reinschreiben!",
    )


class BIAggregationStateRequestSchema(Schema):
    filter_names = fields.List(fields.String(), description="Filter by names", example=["Host foo"])
    filter_groups = fields.List(
        fields.String(), description="Filter by group", example=["My Group"]
    )


class BIAggregationStateResponseSchema(Schema):
    aggregations = fields.Dict(
        description="The Aggregation state",
        example={},
    )
    missing_sites = fields.List(
        fields.String(),
        description="The missing sites",
        example=["beta", "heute"],
    )
    missing_aggr = fields.List(
        fields.String(), description="the missing aggregations", example=["Host heute"]
    )


@Endpoint(
    constructors.domain_type_action_href("bi_aggregation", "aggregation_state"),
    "cmk/get_bi_aggregation_state",
    method="post",
    convert_response=False,
    request_schema=BIAggregationStateRequestSchema,
    response_schema=BIAggregationStateResponseSchema,
    permissions_required=RO_PERMISSIONS,
    tag_group="Monitoring",
    skip_locking=True,
)
def get_bi_aggregation_state(params):
    """Get the state of BI aggregations"""
    user.need_permission("wato.bi_rules")
    filter_config = params.get("body", {})
    filter_names = filter_config.get("filter_names")
    filter_groups = filter_config.get("filter_groups")
    return serve_json(
        api_get_aggregation_state(filter_names=filter_names, filter_groups=filter_groups)
    )


@Endpoint(
    constructors.object_href("bi_aggregation", "{aggregation_id}"),
    "cmk/get_bi_aggregation",
    method="get",
    path_params=[BI_AGGR_ID],
    convert_response=False,
    response_schema=BIAggregationEndpointSchema,
    permissions_required=RO_PERMISSIONS,
)
def get_bi_aggregation(params):
    """Get a BI aggregation"""
    user.need_permission("wato.bi_rules")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    try:
        bi_aggregation = bi_packs.get_aggregation_mandatory(params["aggregation_id"])
    except AggregationNotFoundException:
        _bailout_with_message("Unknown bi_aggregation: %s" % params["aggregation_id"])

    data = {"pack_id": bi_aggregation.pack_id}
    data.update(BIAggregationSchema().dump(bi_aggregation))
    return serve_json(data)


@Endpoint(
    constructors.object_href("bi_aggregation", "{aggregation_id}"),
    "cmk/put_bi_aggregation",
    method="put",
    path_params=[BI_AGGR_ID],
    convert_response=False,
    request_schema=BIAggregationEndpointSchema,
    response_schema=BIAggregationEndpointSchema,
    permissions_required=RW_BI_RULES_PERMISSION,
)
def put_bi_aggregation(params):
    """Update an existing BI aggregation"""
    return _update_bi_aggregation(params, must_exist=True)


@Endpoint(
    constructors.object_href("bi_aggregation", "{aggregation_id}"),
    "cmk/post_bi_aggregation",
    method="post",
    path_params=[BI_AGGR_ID],
    convert_response=False,
    request_schema=BIAggregationEndpointSchema,
    response_schema=BIAggregationEndpointSchema,
    permissions_required=RW_BI_RULES_PERMISSION,
)
def post_bi_aggregation(params):
    """Create a BI aggregation"""
    return _update_bi_aggregation(params, must_exist=False)


def _update_bi_aggregation(params, must_exist: bool):
    user.need_permission("wato.edit")
    user.need_permission("wato.bi_rules")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    aggregation_config = params["body"]
    try:
        target_pack = bi_packs.get_pack_mandatory(aggregation_config["pack_id"])
    except MKGeneralException:
        _bailout_with_message("Unknown bi_pack: %s" % aggregation_config["pack_id"])

    aggregation_id = params["aggregation_id"]
    aggregation_exists = bool(bi_packs.get_aggregation(aggregation_id))
    if aggregation_exists and not must_exist:
        _bailout_with_message("This aggregation_id already exists: %s" % aggregation_id)
    if not aggregation_exists and must_exist:
        _bailout_with_message("This aggregation_id does not exist: %s" % aggregation_id)

    aggregation_config["id"] = aggregation_id
    bi_aggregation = BIAggregation(aggregation_config)
    target_pack.add_aggregation(bi_aggregation)
    bi_packs.save_config()

    data = {"pack_id": bi_aggregation.pack_id}
    data.update(bi_aggregation.schema()().dump(bi_aggregation))
    return serve_json(data)


@Endpoint(
    constructors.object_href("bi_aggregation", "{aggregation_id}"),
    "cmk/delete_bi_aggregation",
    method="delete",
    path_params=[BI_AGGR_ID],
    convert_response=False,
    output_empty=True,
    permissions_required=RW_BI_RULES_PERMISSION,
)
def delete_bi_aggregation(params):
    """Delete a BI aggregation"""
    user.need_permission("wato.edit")
    user.need_permission("wato.bi_rules")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    try:
        bi_aggregation = bi_packs.get_aggregation_mandatory(params["aggregation_id"])
    except AggregationNotFoundException:
        _bailout_with_message("Unknown bi_aggregation: %s" % params["aggregation_id"])

    bi_packs.delete_aggregation(bi_aggregation.id)
    bi_packs.save_config()
    return Response(status=204)


#   .--Packs---------------------------------------------------------------.
#   |                      ____            _                               |
#   |                     |  _ \ __ _  ___| | _____                        |
#   |                     | |_) / _` |/ __| |/ / __|                       |
#   |                     |  __/ (_| | (__|   <\__ \                       |
#   |                     |_|   \__,_|\___|_|\_\___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@Endpoint(
    constructors.collection_href("bi_pack"),
    "cmk/get_bi_packs",
    method="get",
    convert_response=False,
    response_schema=response_schemas.DomainObjectCollection,
    permissions_required=RO_PERMISSIONS,
)
def get_bi_packs(params):
    """Show all BI packs"""
    user.need_permission("wato.bi_rules")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    packs = [
        constructors.collection_item(
            domain_type="bi_pack",
            identifier=pack.id,
            title=pack.title,
        )
        for pack in bi_packs.packs.values()
    ]

    collection_object = constructors.collection_object(
        domain_type="bi_pack",
        value=packs,
        links=[constructors.link_rel("self", constructors.collection_href("bi_pack"))],
    )
    return serve_json(collection_object)


@Endpoint(
    constructors.object_href("bi_pack", "{pack_id}"),
    "cmk/get_bi_pack",
    method="get",
    path_params=[BI_PACK_ID],
    convert_response=False,
    response_schema=response_schemas.DomainObject,
    permissions_required=RO_PERMISSIONS,
)
def get_bi_pack(params):
    """Get a BI pack and its rules and aggregations"""
    user.need_permission("wato.bi_rules")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    bi_pack = bi_packs.get_pack(params["pack_id"])
    if bi_pack is None:
        _bailout_with_message("This pack_id does not exist: %s" % params["pack_id"])
    assert bi_pack is not None

    uri = constructors.object_href("bi_pack", bi_pack.id)
    domain_members = {}
    for (name, entities) in [
        ("aggregation", bi_pack.get_aggregations()),
        ("rule", bi_pack.get_rules()),
    ]:
        elements = entities.values()  # type: ignore[attr-defined]
        domain_members["%ss" % name] = constructors.object_collection(
            name=name,
            domain_type="bi_" + name,  # type: ignore[arg-type]
            entries=[
                constructors.link_rel(
                    rel=".../value",
                    parameters={"collection": "items"},
                    href=constructors.object_href(
                        "bi_" + name, element.id  # type: ignore[arg-type]
                    ),
                )
                for element in elements
            ],
            base=uri,
        )

    extensions = {
        "title": bi_pack.title,
        "contact_groups": bi_pack.contact_groups,
        "public": bi_pack.public,
    }
    domain_object = constructors.domain_object(
        domain_type="bi_pack",
        identifier=bi_pack.id,
        title=bi_pack.title,
        extensions=extensions,
        members=domain_members,
    )

    return serve_json(domain_object)


@Endpoint(
    constructors.object_href("bi_pack", "{pack_id}"),
    "cmk/delete_bi_pack",
    method="delete",
    path_params=[BI_PACK_ID],
    convert_response=False,
    output_empty=True,
    permissions_required=RW_BI_ADMIN_PERMISSIONS,
)
def delete_bi_pack(params):
    """Delete BI pack"""
    user.need_permission("wato.edit")
    user.need_permission("wato.bi_rules")
    user.need_permission("wato.bi_admin")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()

    pack_id = params["pack_id"]
    try:
        target_pack = bi_packs.get_pack_mandatory(pack_id)
    except KeyError:
        _bailout_with_message("Unknown bi_pack: %s" % pack_id)

    num_rules = target_pack.num_rules()
    if num_rules > 0:
        _bailout_with_message(
            "Cannot delete bi_pack %s. It contains %d rules, which might be used in other packs"
            % (pack_id, num_rules)
        )
    bi_packs.delete_pack(pack_id)
    bi_packs.save_config()
    return Response(status=204)


class BIPackEndpointSchema(Schema):
    title = ReqString(
        dump_default="",
        example="BI Title",
        description="TODO: Hier muß Andreas noch etwas reinschreiben!",
    )
    contact_groups = ReqList(
        gui_fields.GroupField(should_exist=True, group_type="contact", example="important_persons"),
        dump_default=[],
        example=["contact", "contactgroup_b"],
        description="TODO: Hier muß Andreas noch etwas reinschreiben!",
    )
    public = ReqBoolean(
        dump_default=False,
        example="false",
        description="TODO: Hier muß Andreas noch etwas reinschreiben!",
    )


@Endpoint(
    constructors.object_href("bi_pack", "{pack_id}"),
    "cmk/put_bi_pack",
    method="put",
    path_params=[BI_PACK_ID],
    convert_response=False,
    request_schema=BIPackEndpointSchema,
    response_schema=BIPackEndpointSchema,
    permissions_required=RW_BI_ADMIN_PERMISSIONS,
)
def put_bi_pack(params):
    """Update an existing BI pack"""
    return _update_bi_pack(params, must_exist=True)


@Endpoint(
    constructors.object_href("bi_pack", "{pack_id}"),
    "cmk/post_bi_pack",
    method="post",
    path_params=[BI_PACK_ID],
    convert_response=False,
    request_schema=BIPackEndpointSchema,
    response_schema=BIPackEndpointSchema,
    permissions_required=RW_BI_ADMIN_PERMISSIONS,
)
def post_bi_pack(params):
    """Create a new BI pack"""
    return _update_bi_pack(params, must_exist=False)


def _update_bi_pack(params, must_exist: bool):
    user.need_permission("wato.edit")
    user.need_permission("wato.bi_rules")
    user.need_permission("wato.bi_admin")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()

    pack_id = params["pack_id"]
    existing_pack = bi_packs.get_pack(pack_id)
    if existing_pack and not must_exist:
        _bailout_with_message("This pack_id already exists: %s" % pack_id)
    if not existing_pack and must_exist:
        _bailout_with_message("This pack_id does not exist: %s" % pack_id)

    pack_config = {}
    if existing_pack:
        # Serialize the old pack
        # Rules and aggregations will be transferred to the new pack
        pack_config.update(existing_pack.serialize())

    pack_config["id"] = pack_id
    pack_config.update(BIPackEndpointSchema().dump(params["body"]))
    new_pack = BIAggregationPack(pack_config)
    bi_packs.add_pack(new_pack)
    bi_packs.save_config()
    return serve_json(BIPackEndpointSchema().dump(new_pack.serialize()))
