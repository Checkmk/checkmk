#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Business intelligence (BI)

BI is used in Checkmk to setup a tree based on the status of hosts and services as branches and to
extend with higher level nodes summarizing (or aggregating) the status of the contained objects.
A BI pack defines the complete tree, consisting of BI aggregations.
Within a BI aggregation a BI rule is used to define the node and its status.

You can find an introduction to BI in the
[Checkmk guide](https://checkmk.com/cms_bi.html).
"""

import http
import http.client

from cmk.gui.http import Response
from cmk.gui.plugins.openapi import fields
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    response_schemas,
)
from cmk.gui.plugins.openapi.utils import ProblemException

from cmk.utils.bi.bi_lib import ReqString
from cmk.utils.bi.bi_rule import BIRule, BIRuleSchema
from cmk.utils.bi.bi_aggregation import BIAggregation, BIAggregationSchema
from cmk.gui.bi import get_cached_bi_packs

BI_RULE_ID = {
    'rule_id': fields.String(example='rule1'),
}
BI_AGGR_ID = {
    'aggregation_id': fields.String(example="aggregation1"),
}
BI_PACK_ID = {
    'pack_id': fields.String(example="pack1"),
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
    pack_id = ReqString(default="", example="pack1")


@Endpoint(constructors.object_href("bi_rule", "{rule_id}"),
          'cmk/get_bi_rule',
          method='get',
          path_params=[BI_RULE_ID],
          response_schema=BIRuleEndpointSchema)
def get_bi_rule(params):
    """Get BI Rule"""
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    try:
        bi_rule = bi_packs.get_rule_mandatory(params["rule_id"])
    except KeyError:
        _bailout_with_message("Unknown bi_rule: %s" % params["rule_id"])

    data = {"pack_id": bi_rule.pack_id}
    data.update(BIRuleSchema().dump(bi_rule))
    return constructors.serve_json(data)


@Endpoint(constructors.object_href("bi_rule", "{rule_id}"),
          'cmk/put_bi_rule',
          method='put',
          path_params=[BI_RULE_ID],
          request_schema=BIRuleEndpointSchema,
          response_schema=BIRuleEndpointSchema)
def put_bi_rule(params):
    """Save BI Rule"""
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    rule_config = params["body"]
    try:
        target_pack = bi_packs.get_pack_mandatory(rule_config["pack_id"])
    except KeyError:
        _bailout_with_message("Unknown bi_pack: %s" % rule_config["pack_id"])

    rule_config["id"] = params["rule_id"]
    bi_rule = BIRule(rule_config)
    target_pack.add_rule(bi_rule)
    bi_packs.save_config()

    data = {"pack_id": bi_rule.pack_id}
    data.update(bi_rule.schema()().dump(bi_rule))
    return constructors.serve_json(data)


@Endpoint(constructors.object_href("bi_rule", "{rule_id}"),
          'cmk/delete_bi_rule',
          method='delete',
          path_params=[BI_RULE_ID],
          output_empty=True)
def delete_bi_rule(params):
    """Delete BI Rule"""
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
    pack_id = ReqString(default="", example="pack1")


@Endpoint(constructors.object_href("bi_aggregation", "{aggregation_id}"),
          'cmk/get_bi_aggregation',
          method='get',
          path_params=[BI_AGGR_ID],
          response_schema=BIAggregationEndpointSchema)
def get_bi_aggregation(params):
    """Get BI Aggregation"""
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    try:
        bi_aggregation = bi_packs.get_aggregation_mandatory(params["aggregation_id"])
    except KeyError:
        _bailout_with_message("Unknown bi_aggregation: %s" % params["aggregation_id"])

    data = {"pack_id": bi_aggregation.pack_id}
    data.update(BIAggregationSchema().dump(bi_aggregation))
    return constructors.serve_json(data)


@Endpoint(constructors.object_href("bi_aggregation", "{aggregation_id}"),
          'cmk/put_bi_aggregation',
          method='put',
          path_params=[BI_AGGR_ID],
          request_schema=BIAggregationEndpointSchema,
          response_schema=BIAggregationEndpointSchema)
def put_bi_aggregation(params):
    """Save BI Aggregation"""
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()

    aggregation_config = params["body"]

    try:
        target_pack = bi_packs.get_pack_mandatory(aggregation_config["pack_id"])
    except KeyError:
        _bailout_with_message("Unknown bi_pack: %s" % aggregation_config["pack_id"])

    aggregation_config["id"] = params["aggregation_id"]
    bi_aggregation = BIAggregation(aggregation_config)
    target_pack.add_aggregation(bi_aggregation)
    bi_packs.save_config()

    data = {"pack_id": bi_aggregation.pack_id}
    data.update(bi_aggregation.schema()().dump(bi_aggregation))
    return constructors.serve_json(data)


@Endpoint(constructors.object_href("bi_aggregation", "{aggregation_id}"),
          'cmk/delete_bi_aggregation',
          method='delete',
          path_params=[BI_AGGR_ID],
          output_empty=True)
def delete_bi_aggregation(params):
    """Delete BI Aggregation"""
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


@Endpoint(constructors.collection_href("bi_pack"),
          'cmk/get_bi_packs',
          method='get',
          response_schema=response_schemas.DomainObjectCollection)
def get_bi_packs(params):
    """Show all BI Packs"""

    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    packs = [
        constructors.collection_item(
            domain_type='bi_pack',
            obj={
                'id': pack.id,
                'title': pack.title,
            },
        ) for pack in bi_packs.packs.values()
    ]

    collection_object = constructors.collection_object(
        domain_type='bi_pack',
        value=packs,
        links=[constructors.link_rel('self', constructors.collection_href('bi_pack'))],
    )
    return constructors.serve_json(collection_object)


@Endpoint(constructors.object_href("bi_pack", "{pack_id}"),
          'cmk/get_bi_pack',
          method='get',
          path_params=[BI_PACK_ID],
          response_schema=response_schemas.DomainObject)
def get_bi_pack(params):
    """Get BI Pack"""
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    bi_pack = bi_packs.get_pack(params["pack_id"])
    if bi_pack is None:
        _bailout_with_message("Unknown bi_pack: %s" % params["pack_id"])
    assert bi_pack is not None

    uri = constructors.object_href('bi_pack', bi_pack.id)
    domain_members = {}
    for (name, entities) in [("aggregation", bi_pack.get_aggregations()),
                             ("rule", bi_pack.get_rules())]:
        elements = entities.values()  # type: ignore[attr-defined]
        domain_members["%ss" % name] = constructors.object_collection(
            name=name,
            domain_type="bi_" + name,  # type: ignore[arg-type]
            entries=[
                constructors.link_rel(
                    rel='.../value',
                    parameters={'collection': "items"},
                    href=constructors.object_href(
                        "bi_" + name  # type: ignore[arg-type]
                        ,
                        element.id),
                ) for element in elements
            ],
            base=uri,
        )

    domain_object = constructors.domain_object(domain_type='bi_pack',
                                               identifier=bi_pack.id,
                                               title=bi_pack.title,
                                               members=domain_members)

    return constructors.serve_json(domain_object)
