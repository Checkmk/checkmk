#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
from collections.abc import Mapping
from typing import Any

from cmk.gui import fields as gui_fields
from cmk.gui.bi import BIManager, get_cached_bi_packs
from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.restful_objects import constructors, Endpoint, response_schemas
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.utils import ProblemException, serve_json
from cmk.gui.utils import permission_verification as permissions

from cmk import fields
from cmk.bi.aggregation import BIAggregation, BIAggregationSchema
from cmk.bi.computer import BIAggregationFilter
from cmk.bi.lib import BIStates, NodeResultBundle, ReqBoolean, ReqList, ReqString
from cmk.bi.packs import (
    AggregationNotFoundException,
    BIAggregationPack,
    DeleteErrorUsedByAggregation,
    DeleteErrorUsedByRule,
    PackNotFoundException,
    RuleNotFoundException,
)
from cmk.bi.rule import BIRule, BIRuleSchema
from cmk.bi.schema import Schema
from cmk.bi.trees import BICompiledRule

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


def _make_error(message):
    return ProblemException(404, http.client.responses[404], message)


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
        description="The identifier of the BI pack.",
    )


RO_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.bi_rules"),
        permissions.Undocumented(
            permissions.AnyPerm(
                [
                    permissions.Perm("bi.see_all"),
                    permissions.Perm("general.see_all"),
                    permissions.OkayToIgnorePerm("mkeventd.seeall"),
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
def get_bi_rule(params: Mapping[str, Any]) -> Response:
    """Show a BI rule"""
    user.need_permission("wato.bi_rules")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    try:
        bi_rule = bi_packs.get_rule_mandatory(params["rule_id"])
    except RuleNotFoundException:
        raise _make_error("Unknown bi_rule: %s" % params["rule_id"])

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
def put_bi_rule(params: Mapping[str, Any]) -> Response:
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
def post_bi_rule(params: Mapping[str, Any]) -> Response:
    """Create a new BI rule"""
    return _update_bi_rule(params, must_exist=False)


def _update_bi_rule(params: Mapping[str, Any], must_exist: bool) -> Response:
    user.need_permission("wato.edit")
    user.need_permission("wato.bi_rules")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    rule_config = params["body"]
    try:
        target_pack = bi_packs.get_pack_mandatory(rule_config["pack_id"])
    except KeyError:
        raise _make_error("Unknown bi_pack: %s" % rule_config["pack_id"])

    rule_id = params["rule_id"]
    rule_exists = bool(bi_packs.get_rule(rule_id))
    if rule_exists and not must_exist:
        raise _make_error("This rule_id already exists: %s" % rule_id)
    if not rule_exists and must_exist:
        raise _make_error("This rule_id does not exist: %s" % rule_id)

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
def delete_bi_rule(params: Mapping[str, Any]) -> Response:
    """Delete BI rule"""
    user.need_permission("wato.edit")
    user.need_permission("wato.bi_rules")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    try:
        bi_rule = bi_packs.get_rule_mandatory(params["rule_id"])
    except RuleNotFoundException:
        raise _make_error("Unknown bi_rule: %s" % params["rule_id"])

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
        description="The identifier of the BI pack.",
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
    "cmk/bi_aggregation_state_post",
    method="post",
    convert_response=False,
    request_schema=BIAggregationStateRequestSchema,
    response_schema=BIAggregationStateResponseSchema,
    permissions_required=RO_PERMISSIONS,
    tag_group="Monitoring",
    skip_locking=True,
    update_config_generation=False,
)
def bi_aggregation_state_post(params: Mapping[str, Any]) -> Response:
    """Get the state of BI aggregations"""

    # This endpoint is being kept for backward compatibility.
    # We now provide the same endpoint via the GET method.

    user.need_permission("wato.bi_rules")
    filter_config = params.get("body", {})
    filter_names = filter_config.get("filter_names")
    filter_groups = filter_config.get("filter_groups")
    return serve_json(_aggregation_state(filter_names=filter_names, filter_groups=filter_groups))


@Endpoint(
    constructors.domain_type_action_href("bi_aggregation", "aggregation_state"),
    "cmk/bi_aggregation_state_get",
    method="get",
    convert_response=False,
    query_params=[BIAggregationStateRequestSchema],
    response_schema=BIAggregationStateResponseSchema,
    permissions_required=RO_PERMISSIONS,
    tag_group="Monitoring",
)
def bi_aggregation_state_get(params: Mapping[str, Any]) -> Response:
    """Get the state of BI aggregations"""
    user.need_permission("wato.bi_rules")
    filter_names = params.get("filter_names")
    filter_groups = params.get("filter_groups")
    return serve_json(_aggregation_state(filter_names=filter_names, filter_groups=filter_groups))


def _aggregation_state(
    filter_names: list[str] | None = None, filter_groups: list[str] | None = None
) -> dict[str, object]:
    bi_manager = BIManager()
    bi_aggregation_filter = BIAggregationFilter(
        [],
        [],
        [],
        filter_names or [],
        filter_groups or [],
        [],
    )

    def collect_infos(
        node_result_bundle: NodeResultBundle, is_single_host_aggregation: bool
    ) -> object:
        actual_result = node_result_bundle.actual_result

        own_infos = {}
        if actual_result.custom_infos:
            own_infos["custom"] = actual_result.custom_infos

        if actual_result.state not in [BIStates.OK, BIStates.PENDING]:
            node_instance = node_result_bundle.instance
            line_tokens = []
            if isinstance(node_instance, BICompiledRule):
                line_tokens.append(node_instance.properties.title)
            else:
                node_info = []
                if not is_single_host_aggregation:
                    node_info.append(node_instance.host_name)
                if node_instance.service_description:
                    node_info.append(node_instance.service_description)
                if node_info:
                    line_tokens.append("/".join(node_info))
            if actual_result.output:
                line_tokens.append(actual_result.output)
            own_infos["error"] = {"state": actual_result.state, "output": ", ".join(line_tokens)}

        nested_infos = [
            x
            for y in node_result_bundle.nested_results
            for x in [collect_infos(y, is_single_host_aggregation)]
            if x is not None
        ]

        if own_infos or nested_infos:
            return [own_infos, nested_infos]
        return None

    aggregations = {}
    results = bi_manager.computer.compute_result_for_filter(bi_aggregation_filter)
    for _compiled_aggregation, node_result_bundles in results:
        for node_result_bundle in node_result_bundles:
            aggr_title = node_result_bundle.instance.properties.title
            required_hosts = [x[1] for x in node_result_bundle.instance.get_required_hosts()]
            is_single_host_aggregation = len(required_hosts) == 1
            aggregations[aggr_title] = {
                "state": node_result_bundle.actual_result.state,
                "output": node_result_bundle.actual_result.output,
                "hosts": required_hosts,
                "acknowledged": node_result_bundle.actual_result.acknowledged,
                "in_downtime": node_result_bundle.actual_result.in_downtime != 0,
                "in_service_period": node_result_bundle.actual_result.in_service_period,
                "infos": collect_infos(node_result_bundle, is_single_host_aggregation),
            }

    have_sites = {x[0] for x in bi_manager.status_fetcher.states}
    missing_aggregations = []
    required_sites = set()
    required_aggregations = bi_manager.computer.get_required_aggregations(bi_aggregation_filter)
    for _bi_aggregation, branches in required_aggregations:
        for branch in branches:
            branch_sites = {x[0] for x in branch.required_elements()}
            required_sites.update(branch_sites)
            if branch.properties.title not in aggregations:
                missing_aggregations.append(branch.properties.title)

    response: dict[str, object] = {
        "aggregations": aggregations,
        "missing_sites": list(required_sites - have_sites),
        "missing_aggr": missing_aggregations,
    }
    return response


@Endpoint(
    constructors.object_href("bi_aggregation", "{aggregation_id}"),
    "cmk/get_bi_aggregation",
    method="get",
    path_params=[BI_AGGR_ID],
    convert_response=False,
    response_schema=BIAggregationEndpointSchema,
    permissions_required=RO_PERMISSIONS,
)
def get_bi_aggregation(params: Mapping[str, Any]) -> Response:
    """Get a BI aggregation"""
    user.need_permission("wato.bi_rules")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    try:
        bi_aggregation = bi_packs.get_aggregation_mandatory(params["aggregation_id"])
    except AggregationNotFoundException:
        raise _make_error("Unknown bi_aggregation: %s" % params["aggregation_id"])

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
def put_bi_aggregation(params: Mapping[str, Any]) -> Response:
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
def post_bi_aggregation(params: Mapping[str, Any]) -> Response:
    """Create a BI aggregation"""
    return _update_bi_aggregation(params, must_exist=False)


def _update_bi_aggregation(params: Mapping[str, Any], must_exist: bool) -> Response:
    user.need_permission("wato.edit")
    user.need_permission("wato.bi_rules")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    aggregation_config = params["body"]
    try:
        target_pack = bi_packs.get_pack_mandatory(aggregation_config["pack_id"])
    except PackNotFoundException:
        raise _make_error("Unknown bi_pack: %s" % aggregation_config["pack_id"])

    aggregation_id = params["aggregation_id"]
    aggregation_exists = bool(bi_packs.get_aggregation(aggregation_id))
    if aggregation_exists and not must_exist:
        raise _make_error("This aggregation_id already exists: %s" % aggregation_id)
    if not aggregation_exists and must_exist:
        raise _make_error("This aggregation_id does not exist: %s" % aggregation_id)

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
def delete_bi_aggregation(params: Mapping[str, Any]) -> Response:
    """Delete a BI aggregation"""
    user.need_permission("wato.edit")
    user.need_permission("wato.bi_rules")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    try:
        bi_aggregation = bi_packs.get_aggregation_mandatory(params["aggregation_id"])
    except AggregationNotFoundException:
        raise _make_error("Unknown bi_aggregation: %s" % params["aggregation_id"])

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
def get_bi_packs(params: Mapping[str, Any]) -> Response:
    """Show all BI packs"""
    user.need_permission("wato.bi_rules")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()

    collection_object = constructors.collection_object(
        domain_type="bi_pack",
        value=[
            constructors.collection_item(
                domain_type="bi_pack",
                identifier=pack.id,
                title=pack.title,
            )
            for pack in bi_packs.packs.values()
        ],
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
def get_bi_pack(params: Mapping[str, Any]) -> Response:
    """Get a BI pack and its rules and aggregations"""
    user.need_permission("wato.bi_rules")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()
    bi_pack = bi_packs.get_pack(params["pack_id"])
    if bi_pack is None:
        raise _make_error("This pack_id does not exist: %s" % params["pack_id"])
    assert bi_pack is not None

    uri = constructors.object_href("bi_pack", bi_pack.id)
    domain_members = {}
    for name, entities in [
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
                        "bi_" + name,  # type: ignore[arg-type]
                        element.id,
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
def delete_bi_pack(params: Mapping[str, Any]) -> Response:
    """Delete BI pack"""
    user.need_permission("wato.edit")
    user.need_permission("wato.bi_rules")
    user.need_permission("wato.bi_admin")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()

    pack_id = params["pack_id"]
    try:
        target_pack = bi_packs.get_pack_mandatory(pack_id)
    except PackNotFoundException:
        raise _make_error("Unknown bi_pack: %s" % pack_id)

    num_rules = target_pack.num_rules()
    if num_rules > 0:
        raise _make_error(
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
        description="The title of the BI pack.",
    )
    contact_groups = ReqList(
        gui_fields.GroupField(should_exist=True, group_type="contact", example="important_persons"),
        dump_default=[],
        example=["contact", "contactgroup_b"],
        description="A list of contact group identifiers.",
    )
    public = ReqBoolean(
        dump_default=False,
        example="false",
        description="Should the BI pack be public or not.",
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
def put_bi_pack(params: Mapping[str, Any]) -> Response:
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
def post_bi_pack(params: Mapping[str, Any]) -> Response:
    """Create a new BI pack"""
    return _update_bi_pack(params, must_exist=False)


def _update_bi_pack(params: Mapping[str, Any], must_exist: bool) -> Response:
    user.need_permission("wato.edit")
    user.need_permission("wato.bi_rules")
    user.need_permission("wato.bi_admin")
    bi_packs = get_cached_bi_packs()
    bi_packs.load_config()

    pack_id = params["pack_id"]
    existing_pack = bi_packs.get_pack(pack_id)
    if existing_pack and not must_exist:
        raise _make_error("This pack_id already exists: %s" % pack_id)
    if not existing_pack and must_exist:
        raise _make_error("This pack_id does not exist: %s" % pack_id)

    if existing_pack:
        # Serialize the old pack
        # Rules and aggregations will be transferred to the new pack
        pack_config = existing_pack.serialize()
        pack_config.update(BIPackEndpointSchema().dump(params["body"]))
    else:
        pack_config = BIPackEndpointSchema().dump(params["body"])

    pack_config["id"] = pack_id

    new_pack = BIAggregationPack(pack_config)
    bi_packs.add_pack(new_pack)
    bi_packs.save_config()
    return serve_json(BIPackEndpointSchema().dump(new_pack.serialize()))


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(get_bi_rule, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(put_bi_rule, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(post_bi_rule, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete_bi_rule, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(bi_aggregation_state_post, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(bi_aggregation_state_get, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(get_bi_aggregation, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(put_bi_aggregation, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(post_bi_aggregation, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete_bi_aggregation, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(get_bi_packs, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(get_bi_pack, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete_bi_pack, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(put_bi_pack, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(post_bi_pack, ignore_duplicates=ignore_duplicates)
