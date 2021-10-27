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
from cmk.utils.bi.bi_packs import BIAggregationPack
from cmk.utils.bi.bi_rule import BIRule, BIRuleSchema
from cmk.utils.bi.bi_schema import Schema

from cmk.gui import fields
from cmk.gui.bi import get_cached_bi_packs
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.restful_objects import constructors, Endpoint, response_schemas
from cmk.gui.plugins.openapi.utils import ProblemException

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


@Endpoint(
    constructors.object_href("bi_rule", "{rule_id}"),
    "cmk/get_bi_rule",
    method="get",
    path_params=[BI_RULE_ID],
    convert_response=False,
    response_schema=BIRuleEndpointSchema,
)
def get_bi_rule(params):
    """Show a BI rule"""
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    try:
        bi_rule = bi_packs.get_rule_mandatory(params["rule_id"])
    except KeyError:
        _bailout_with_message("Unknown bi_rule: %s" % params["rule_id"])

    data = {"pack_id": bi_rule.pack_id}
    data.update(BIRuleSchema().dump(bi_rule))
    return constructors.serve_json(data)


@Endpoint(
    constructors.object_href("bi_rule", "{rule_id}"),
    "cmk/put_bi_rule",
    method="put",
    path_params=[BI_RULE_ID],
    convert_response=False,
    request_schema=BIRuleEndpointSchema,
    response_schema=BIRuleEndpointSchema,
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
)
def post_bi_rule(params):
    """Create a new BI rule"""
    return _update_bi_rule(params, must_exist=False)


def _update_bi_rule(params, must_exist: bool):
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
    return constructors.serve_json(data)


@Endpoint(
    constructors.object_href("bi_rule", "{rule_id}"),
    "cmk/delete_bi_rule",
    method="delete",
    path_params=[BI_RULE_ID],
    convert_response=False,
    output_empty=True,
)
def delete_bi_rule(params):
    """Delete BI rule"""
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    try:
        bi_rule = bi_packs.get_rule_mandatory(params["rule_id"])
    except KeyError:
        _bailout_with_message("Unknown bi_rule: %s" % params["rule_id"])

    bi_packs.delete_rule(bi_rule.id)
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


@Endpoint(
    constructors.object_href("bi_aggregation", "{aggregation_id}"),
    "cmk/get_bi_aggregation",
    method="get",
    path_params=[BI_AGGR_ID],
    convert_response=False,
    response_schema=BIAggregationEndpointSchema,
)
def get_bi_aggregation(params):
    """Get a BI aggregation"""
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    try:
        bi_aggregation = bi_packs.get_aggregation_mandatory(params["aggregation_id"])
    except KeyError:
        _bailout_with_message("Unknown bi_aggregation: %s" % params["aggregation_id"])

    data = {"pack_id": bi_aggregation.pack_id}
    data.update(BIAggregationSchema().dump(bi_aggregation))
    return constructors.serve_json(data)


@Endpoint(
    constructors.object_href("bi_aggregation", "{aggregation_id}"),
    "cmk/put_bi_aggregation",
    method="put",
    path_params=[BI_AGGR_ID],
    convert_response=False,
    request_schema=BIAggregationEndpointSchema,
    response_schema=BIAggregationEndpointSchema,
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
)
def post_bi_aggregation(params):
    """Create a BI aggregation"""
    return _update_bi_aggregation(params, must_exist=False)


def _update_bi_aggregation(params, must_exist: bool):
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    aggregation_config = params["body"]
    try:
        target_pack = bi_packs.get_pack_mandatory(aggregation_config["pack_id"])
    except KeyError:
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
    return constructors.serve_json(data)


@Endpoint(
    constructors.object_href("bi_aggregation", "{aggregation_id}"),
    "cmk/delete_bi_aggregation",
    method="delete",
    path_params=[BI_AGGR_ID],
    convert_response=False,
    output_empty=True,
)
def delete_bi_aggregation(params):
    """Delete a BI aggregation"""
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    try:
        bi_aggregation = bi_packs.get_aggregation_mandatory(params["aggregation_id"])
    except KeyError:
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
)
def get_bi_packs(params):
    """Show all BI packs"""

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
    return constructors.serve_json(collection_object)


@Endpoint(
    constructors.object_href("bi_pack", "{pack_id}"),
    "cmk/get_bi_pack",
    method="get",
    path_params=[BI_PACK_ID],
    convert_response=False,
    response_schema=response_schemas.DomainObject,
)
def get_bi_pack(params):
    """Get a BI pack and its rules and aggregations"""
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

    return constructors.serve_json(domain_object)


@Endpoint(
    constructors.object_href("bi_pack", "{pack_id}"),
    "cmk/delete_bi_pack",
    method="delete",
    path_params=[BI_PACK_ID],
    convert_response=False,
    output_empty=True,
)
def delete_bi_pack(params):
    """Delete BI pack"""
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
        fields.String(),
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
)
def post_bi_pack(params):
    """Create a new BI pack"""
    return _update_bi_pack(params, must_exist=False)


def _update_bi_pack(params, must_exist: bool):
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
    return constructors.serve_json(BIPackEndpointSchema().dump(new_pack.serialize()))
