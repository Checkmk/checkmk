#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Rules"""
from __future__ import annotations

import dataclasses
import typing

from cmk.utils.type_defs import RuleOptions

from cmk.gui import exceptions, http, watolib
from cmk.gui.globals import user
from cmk.gui.i18n import _, _l
from cmk.gui.plugins.openapi.endpoints.rule.fields import (
    InputRuleObject,
    MoveRuleTo,
    RULE_ID,
    RuleCollection,
    RuleObject,
    RuleSearchOptions,
)
from cmk.gui.plugins.openapi.restful_objects import constructors, Endpoint, permissions
from cmk.gui.plugins.openapi.restful_objects.datastructures import denilled
from cmk.gui.plugins.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.plugins.openapi.utils import problem, ProblemException, serve_json
from cmk.gui.utils import gen_id
from cmk.gui.utils.escaping import strip_tags
from cmk.gui.watolib import add_change, make_diff_text
from cmk.gui.watolib.rulesets import RuleConditions

PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.rulesets"),
        permissions.Optional(permissions.Perm("wato.all_folders")),
    ]
)

RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        *PERMISSIONS.perms,
    ]
)


# NOTE: This is a dataclass and no namedtuple because it needs to be mutable. See `move_rule_to`
@dataclasses.dataclass
class RuleEntry:
    rule: watolib.Rule
    ruleset: watolib.Ruleset
    all_rulesets: watolib.AllRulesets
    # NOTE: Can't be called "index", because mypy doesn't like that. Duh.
    index_nr: int
    folder: watolib.CREFolder


def _validate_rule_move(lhs: RuleEntry, rhs: RuleEntry) -> None:
    if lhs.ruleset.name != rhs.ruleset.name:
        raise ProblemException(
            title="Invalid rule move.", detail="The two rules are not in the same ruleset."
        )
    if lhs.rule.id == rhs.rule.id:
        raise ProblemException(
            title="Invalid rule move", detail="You cannot move a rule before/after itself."
        )


@Endpoint(
    constructors.object_action_href("rule", "{rule_id}", "move"),
    "cmk/move",
    method="post",
    etag="input",
    path_params=[RULE_ID],
    request_schema=MoveRuleTo,
    response_schema=RuleObject,
    permissions_required=RW_PERMISSIONS,
)
def move_rule_to(param: typing.Mapping[str, typing.Any]) -> http.Response:
    """Move a rule to a specific location"""
    user.need_permission("wato.edit")
    user.need_permission("wato.rulesets")
    rule_id = param["rule_id"]

    body = param["body"]
    position = body["position"]

    source_entry = _get_rule_by_id(rule_id)

    all_rulesets = source_entry.all_rulesets

    index: int
    dest_folder: watolib.CREFolder
    if position == "top_of_folder":
        dest_folder = body["folder"]
        index = watolib.Ruleset.TOP
    elif position == "bottom_of_folder":
        dest_folder = body["folder"]
        index = watolib.Ruleset.BOTTOM
    elif position == "before_specific_rule":
        dest_entry = _get_rule_by_id(body["rule_id"], all_rulesets=all_rulesets)
        _validate_rule_move(source_entry, dest_entry)
        index = dest_entry.index_nr
        dest_folder = dest_entry.folder
    elif position == "after_specific_rule":
        dest_entry = _get_rule_by_id(body["rule_id"], all_rulesets=all_rulesets)
        _validate_rule_move(source_entry, dest_entry)
        dest_folder = dest_entry.folder
        index = dest_entry.index_nr + 1
    else:
        return problem(
            status=400,
            title="Invalid position",
            detail=f"Position {position!r} is not a valid position.",
        )

    dest_folder.need_permission("write")
    source_entry.ruleset.move_to_folder(source_entry.rule, dest_folder, index)
    source_entry.folder = dest_folder
    all_rulesets.save()
    affected_sites = source_entry.folder.all_site_ids()

    if dest_folder != source_entry.folder:
        affected_sites.extend(dest_folder.all_site_ids())

    add_change(
        "edit-rule",
        _('Changed properties of rule "%s", moved from folder "%s" to top of folder "%s"')
        % (source_entry.rule.id, source_entry.folder.title(), dest_folder.title()),
        sites=list(set(affected_sites)),
        object_ref=source_entry.rule.object_ref(),
    )

    return serve_json(_serialize_rule(source_entry))


@Endpoint(
    constructors.collection_href("rule"),
    "cmk/create",
    method="post",
    etag="output",
    request_schema=InputRuleObject,
    response_schema=RuleObject,
    permissions_required=RW_PERMISSIONS,
)
def create_rule(param):
    """Create rule"""
    user.need_permission("wato.edit")
    user.need_permission("wato.rulesets")
    body = param["body"]
    folder: watolib.CREFolder = body["folder"]
    value = body["value_raw"]
    ruleset_name = body["ruleset"]

    folder.need_permission("write")

    rulesets = watolib.FolderRulesets(folder)
    rulesets.load()
    try:
        ruleset = rulesets.get(ruleset_name)
    except KeyError:
        return problem(
            status=400,
            detail=f"Ruleset {ruleset_name!r} could not be found.",
        )

    try:
        ruleset.valuespec().validate_value(value, "")
    except exceptions.MKUserError as exc:
        if exc.varname is None:
            title = "A field has a problem"
        else:
            field_name = strip_tags(exc.varname.replace("_p_", ""))
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
            host_folder=folder.path(),
            host_tags=body["conditions"].get("host_tags"),
            host_labels=body["conditions"].get("host_labels"),
            host_name=body["conditions"].get("host_name"),
            service_description=body["conditions"].get("service_description"),
            service_labels=body["conditions"].get("service_labels"),
        ),
        RuleOptions.from_config(body["properties"]),
        value,
    )
    index = ruleset.append_rule(folder, rule)
    rulesets.save()
    # TODO Duplicated code is in pages/rulesets.py:2670-
    # TODO Move to
    add_change(
        "new-rule",
        _l('Created new rule #%d in ruleset "%s" in folder "%s"')
        % (index, ruleset.title(), folder.alias_path()),
        sites=folder.all_site_ids(),
        diff_text=make_diff_text({}, rule.to_log()),
        object_ref=rule.object_ref(),
    )
    rule_entry = _get_rule_by_id(rule.id)
    return serve_json(_serialize_rule(rule_entry))


@Endpoint(
    constructors.collection_href(domain_type="rule"),
    ".../collection",
    method="get",
    response_schema=RuleCollection,
    permissions_required=PERMISSIONS,
    query_params=[RuleSearchOptions],
)
def list_rules(param):
    """List rules"""
    user.need_permission("wato.rulesets")
    all_rulesets = watolib.AllRulesets()
    all_rulesets.load()
    ruleset_name = param["ruleset_name"]

    try:
        ruleset = all_rulesets.get(ruleset_name)
    except KeyError:
        try:
            # this should have been removed with Change-Id I1a85858fc8881f416f96f4b3f069f558d896b844
            # as customers could have written scripts where this replacement
            # could return a valid response we keep it in the 2.1.0 branch.
            ruleset = all_rulesets.get(ruleset_name.replace("-", ":"))
        except KeyError:
            return problem(
                status=400,
                title="Unknown ruleset.",
                detail=f"The ruleset of name {ruleset_name!r} is not known.",
            )

    result = []
    for folder, index, rule in ruleset.get_rules():
        result.append(
            _serialize_rule(
                RuleEntry(
                    rule=rule,
                    ruleset=rule.ruleset,
                    folder=folder,
                    index_nr=index,
                    all_rulesets=all_rulesets,
                )
            )
        )

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
    permissions_required=PERMISSIONS,
)
def show_rule(param):
    """Show a rule"""
    user.need_permission("wato.rulesets")
    rule_entry = _get_rule_by_id(param["rule_id"])
    return serve_json(_serialize_rule(rule_entry))


def _get_rule_by_id(rule_uuid: str, all_rulesets=None) -> RuleEntry:
    if all_rulesets is None:
        all_rulesets = watolib.AllRulesets()
        all_rulesets.load()

    for ruleset in all_rulesets.get_rulesets().values():
        folder: watolib.CREFolder
        index: int
        rule: watolib.Rule
        for folder, index, rule in ruleset.get_rules():
            if rule.id == rule_uuid:
                return RuleEntry(
                    index_nr=index,
                    rule=rule,
                    folder=folder,
                    ruleset=ruleset,
                    all_rulesets=all_rulesets,
                )

    raise ProblemException(
        status=404,
        title="Unknown rule.",
        detail=f"Rule with UUID '{rule_uuid}' was not found.",
    )


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
    permissions_required=RW_PERMISSIONS,
)
def delete_rule(param):
    """Delete a rule"""
    user.need_permission("wato.edit")
    user.need_permission("wato.rulesets")
    rule_id = param["rule_id"]
    rule: watolib.Rule
    all_rulesets = watolib.AllRulesets()
    all_rulesets.load()

    found = False
    for ruleset in all_rulesets.get_rulesets().values():
        for _folder, _index, rule in ruleset.get_rules():
            if rule.id == rule_id:
                ruleset.delete_rule(rule)
                all_rulesets.save()
                found = True
    if found:
        return http.Response(status=204)

    return problem(
        status=404,
        title="Rule not found.",
        detail=f"The rule with ID {rule_id!r} could not be found.",
    )


def _serialize_rule(rule_entry: RuleEntry) -> DomainObject:
    rule = rule_entry.rule
    return constructors.domain_object(
        domain_type="rule",
        editable=False,
        identifier=rule.id,
        title=rule.description(),
        extensions={
            "ruleset": rule.ruleset.name,
            "folder": "/" + rule_entry.folder.path(),
            "folder_index": rule_entry.index_nr,
            "properties": rule.rule_options.to_config(),
            "value_raw": repr(rule.ruleset.valuespec().mask(rule.value)),
            "conditions": denilled(
                {
                    "host_name": rule.conditions.host_name,
                    "host_tags": rule.conditions.host_tags,
                    "host_labels": rule.conditions.host_labels,
                    "service_description": rule.conditions.service_description,
                    "service_labels": rule.conditions.service_labels,
                }
            ),
        },
    )
