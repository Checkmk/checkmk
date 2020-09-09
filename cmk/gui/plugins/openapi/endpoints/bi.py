#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Business intelligence"""

import http
from connexion import ProblemException  # type: ignore

from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    endpoint_schema,
    response_schemas,
)
from cmk.gui.plugins.openapi.restful_objects.type_defs import (
    ParamDict,)

from cmk.utils.bi.bi_lib import ReqString
from cmk.utils.bi.bi_packs import bi_packs
from cmk.utils.bi.bi_rule import BIRule, BIRuleSchema
from cmk.utils.bi.bi_aggregation import BIAggregation, BIAggregationSchema

BI_RULE_ID = ParamDict.create("rule_id", "query")
BI_AGGR_ID = ParamDict.create("aggregation_id", "query")
BI_PACK_ID = ParamDict.create("pack_id", "query")

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


@endpoint_schema(constructors.object_href("bi_rule", "{rule_id}"),
                 'cmk/get_bi_rule',
                 method='get',
                 parameters=[BI_RULE_ID(location="path", example="rule1")],
                 request_body_required=False,
                 response_schema=BIRuleEndpointSchema)
def get_bi_rule(params):
    """Get BI Rule"""
    bi_packs.load_config()
    bi_rule = bi_packs.get_rule(params["rule_id"])
    if bi_rule is None:
        _bailout_with_message("Unknown bi_rule: %s" % params["rule_id"])
    assert bi_rule is not None

    data = {"pack_id": bi_rule.pack_id}
    data.update(BIRuleSchema().dump(bi_rule).data)
    return constructors.serve_json(data)


@endpoint_schema(constructors.object_href("bi_rule", "{rule_id}"),
                 'cmk/put_bi_rule',
                 method='put',
                 parameters=[BI_RULE_ID(location="path", example="rule1")],
                 request_body_required=True,
                 request_schema=BIRuleEndpointSchema,
                 response_schema=BIRuleEndpointSchema)
def put_bi_rule(params):
    """Save BI Rule"""
    bi_packs.load_config()
    target_pack = bi_packs.get_pack(params["body"]["pack_id"])
    if target_pack is None:
        _bailout_with_message("Unknown bi_pack: %s" % params["body"]["pack_id"])
    assert target_pack is not None

    bi_rule = BIRule(params["body"])
    target_pack.add_rule(bi_rule)
    bi_packs.save_config()

    data = {"pack_id": bi_rule.pack_id}
    data.update(bi_rule.schema()().dump(bi_rule).data)
    return constructors.serve_json(data)


def _bailout_with_message(message):
    raise ProblemException(404, http.client.responses[404], message)


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


@endpoint_schema(constructors.object_href("bi_aggregation", "{aggregation_id}"),
                 'cmk/get_bi_aggregation',
                 method='get',
                 parameters=[BI_AGGR_ID(location="path", example="aggregation1")],
                 request_body_required=False,
                 response_schema=BIAggregationEndpointSchema)
def get_bi_aggregation(params):
    """Get BI Aggregation"""
    bi_packs.load_config()
    bi_aggregation = bi_packs.get_aggregation(params["aggregation_id"])
    if bi_aggregation is None:
        _bailout_with_message("Unknown bi_aggregation: %s" % params["aggregation_id"])
    assert bi_aggregation is not None

    data = {"pack_id": bi_aggregation.pack_id}
    data.update(BIAggregationSchema().dump(bi_aggregation).data)
    return constructors.serve_json(data)


@endpoint_schema(constructors.object_href("bi_aggregation", "{aggregation_id}"),
                 'cmk/put_bi_aggregation',
                 method='put',
                 parameters=[BI_AGGR_ID(location="path", example="aggregation1")],
                 request_body_required=True,
                 request_schema=BIAggregationEndpointSchema,
                 response_schema=BIAggregationEndpointSchema)
def put_bi_aggregation(params):
    """Save BI Aggregation"""
    bi_packs.load_config()
    bi_aggregation = BIAggregation(params["body"])

    target_pack = bi_packs.get_pack(params["body"]["pack_id"])
    if target_pack is None:
        _bailout_with_message("Unknown bi_pack: %s" % params["body"]["pack_id"])

    assert target_pack is not None
    target_pack.add_aggregation(bi_aggregation)
    bi_packs.save_config()

    data = {"pack_id": bi_aggregation.pack_id}
    data.update(bi_aggregation.schema()().dump(bi_aggregation).data)
    return constructors.serve_json(data)


#   .--Packs---------------------------------------------------------------.
#   |                      ____            _                               |
#   |                     |  _ \ __ _  ___| | _____                        |
#   |                     | |_) / _` |/ __| |/ / __|                       |
#   |                     |  __/ (_| | (__|   <\__ \                       |
#   |                     |_|   \__,_|\___|_|\_\___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@endpoint_schema(constructors.collection_href("bi_pack"),
                 'cmk/get_bi_packs',
                 method='get',
                 request_body_required=False,
                 response_schema=response_schemas.DomainObjectCollection)
def get_bi_packs(params):
    """Show all BI Packs"""

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


@endpoint_schema(constructors.object_href("bi_pack", "{pack_id}"),
                 'cmk/get_bi_pack',
                 method='get',
                 parameters=[BI_PACK_ID(location="path", example="pack1")],
                 request_body_required=False,
                 response_schema=response_schemas.DomainObjectCollection)
def get_bi_pack(params):
    """Get BI Pack"""
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
