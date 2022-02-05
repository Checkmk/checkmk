#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Rules"""
from __future__ import annotations

import typing

from cmk.gui.plugins.openapi.restful_objects.datastructures import denilled

if typing.TYPE_CHECKING:
    from typing import Tuple

from cmk.utils.type_defs import RuleOptions

from cmk.gui import exceptions, http, watolib
from cmk.gui.i18n import _l
from cmk.gui.plugins.openapi.endpoints.rule.fields import (
    InputRuleObject,
    RULE_ID,
    RuleCollection,
    RuleObject,
    RuleSearchOptions,
)
from cmk.gui.plugins.openapi.restful_objects import constructors, Endpoint
from cmk.gui.plugins.openapi.restful_objects.constructors import serve_json
from cmk.gui.plugins.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.plugins.openapi.utils import problem
from cmk.gui.utils import gen_id
from cmk.gui.utils.escaping import strip_tags
from cmk.gui.watolib import add_change, make_diff_text
from cmk.gui.watolib.rulesets import RuleConditions

# TODO: move a rule within a ruleset


@Endpoint(
    constructors.collection_href("rule"),
    "cmk/create",
    method="post",
    etag="output",
    request_schema=InputRuleObject,
    response_schema=RuleObject,
)
def create_rule(param):
    """Create rule"""
    body = param["body"]
    folder = body["folder"]
    value = body["value_raw"]
    rulesets = watolib.FolderRulesets(folder)
    rulesets.load()
    try:
        ruleset = rulesets.get(body["ruleset"])
    except KeyError:
        return problem(
            status=400,
            detail=f"Ruleset {body['ruleset']!r} could not be found.",
        )

    try:
        ruleset.valuespec().validate_value(value, "")
    except exceptions.MKUserError as exc:
        if exc.varname is None:
            title = "A field has a problem"
        else:
            field_name = exc.varname.replace("_p_", "")
            title = f"Problem in (sub-)field {field_name!r}"

        return problem(
            status=400,
            detail=strip_tags(exc.message),
            title=title,
        )

    rule = watolib.Rule(
        gen_id(),
        folder,
        ruleset,
        RuleConditions(
            host_folder=folder,
            host_tags=body["conditions"].get("host_tag"),
            host_labels=body["conditions"].get("host_label"),
            host_name=body["conditions"].get("host_name"),
            service_description=body["conditions"].get("service_description"),
            service_labels=body["conditions"].get("service_label"),
        ),
        RuleOptions.from_config(body["properties"]),
        value,
    )
    index = ruleset.append_rule(folder, rule)
    rulesets.save()
    # TODO Duplicated code is in pages/rulesets.py:2670-
    # TODO Move to watolib
    add_change(
        "new-rule",
        _l('Created new rule #%d in ruleset "%s" in folder "%s"')
        % (index, ruleset.title(), folder.alias_path()),
        sites=folder.all_site_ids(),
        diff_text=make_diff_text({}, rule.to_log()),
        object_ref=rule.object_ref(),
    )
    return serve_json(_serialize_rule(folder, index, rule))


@Endpoint(
    constructors.collection_href(domain_type="rule"),
    ".../collection",
    method="get",
    response_schema=RuleCollection,
    query_params=[RuleSearchOptions],
)
def list_rules(param):
    """List rules"""
    all_sets = watolib.AllRulesets()
    all_sets.load()
    ruleset = all_sets.get(param["ruleset_name"].replace("-", ":"))

    result = []
    for folder, index, rule in ruleset.get_rules():
        result.append(_serialize_rule(folder, index, rule))

    return serve_json(
        constructors.collection_object(
            domain_type="rule",
            value=result,
            extensions={
                "found_rules": len(result),
            },
        )
    )


@Endpoint(
    constructors.object_href(domain_type="rule", obj_id="{rule_id}"),
    "cmk/show",
    method="get",
    response_schema=RuleObject,
    path_params=[RULE_ID],
)
def show_rule(param):
    """Show a rule"""
    rule: watolib.Rule
    _, folder, index, rule = _get_rule_by_id(param["rule_id"])
    return serve_json(_serialize_rule(folder, index, rule))


def _get_rule_by_id(rule_uuid: str) -> Tuple[watolib.Ruleset, watolib.CREFolder, int, watolib.Rule]:
    all_sets = watolib.AllRulesets()
    all_sets.load()
    for ruleset in all_sets.get_rulesets().values():
        for folder, index, rule in ruleset.get_rules():
            if rule.id == rule_uuid:
                return ruleset, folder, index, rule
    raise KeyError(f"Rule with UUID {rule_uuid} was not found.")


@Endpoint(
    constructors.object_href(domain_type="rule", obj_id="{rule_id}"),
    ".../delete",
    method="delete",
    path_params=[RULE_ID],
    output_empty=True,
    status_descriptions={
        204: "Rule was deleted successfully.",
        404: "The rule to be deleted was not found.",
    },
    additional_status_codes=[
        204,
        404,
    ],
)
def delete_rule(param):
    """Delete a rule"""
    rule_id = param["rule_id"]
    rule: watolib.Rule
    all_sets = watolib.AllRulesets()
    all_sets.load()

    found = False
    for ruleset in all_sets.get_rulesets().values():
        for _folder, _index, rule in ruleset.get_rules():
            if rule.id == rule_id:
                ruleset.delete_rule(rule)
                all_sets.save()
                found = True
    if found:
        return http.Response(status=204)

    return problem(
        status=404,
        title="Rule not found.",
        detail=f"The rule with ID {rule_id!r} could not be found.",
    )


def _serialize_rule(
    folder: watolib.CREFolder,
    index: int,
    rule: watolib.Rule,
) -> DomainObject:
    return constructors.domain_object(
        domain_type="rule",
        identifier=rule.id,
        title=rule.description(),
        extensions={
            "ruleset": rule.ruleset.name,
            "folder": "/" + folder.path(),
            "folder_index": index,
            "properties": rule.rule_options.to_config(),
            "value_raw": rule.value,
            "conditions": denilled(
                {
                    "host_name": rule.conditions.host_name,
                    "host_tag": rule.conditions.host_tags,
                    "host_label": rule.conditions.host_labels,
                    "service_description": rule.conditions.service_description,
                    "service_label": rule.conditions.service_labels,
                }
            ),
        },
    )
