#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Rules"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from typing import Any

from cmk.utils.datastructures import denilled
from cmk.utils.labels import LabelGroups
from cmk.utils.rulesets.conditions import (
    allow_host_label_conditions,
    allow_service_label_conditions,
)
from cmk.utils.rulesets.ruleset_matcher import RuleOptionsSpec

from cmk.gui import exceptions, http
from cmk.gui.config import active_config
from cmk.gui.i18n import _l
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.rule.fields import (
    APILabelGroupCondition,
    InputRuleObject,
    MoveRuleTo,
    RULE_ID,
    RuleCollection,
    RuleObject,
    RuleSearchOptions,
    UpdateRuleObject,
)
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.openapi.utils import (
    problem,
    ProblemException,
    RestAPIRequestDataValidationException,
    serve_json,
)
from cmk.gui.utils import gen_id
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.utils.escaping import strip_tags
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_quick_setup
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.rulesets import (
    AllRulesets,
    FolderRulesets,
    Rule,
    RuleConditions,
    RuleOptions,
    Ruleset,
    RulesetCollection,
    visible_ruleset,
    visible_rulesets,
)


class FieldValidationException(Exception):
    title: str
    detail: str


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
    rule: Rule
    ruleset: Ruleset
    all_rulesets: AllRulesets
    # NOTE: Can't be called "index", because mypy doesn't like that. Duh.
    index_nr: int
    folder: Folder


def _validate_rule_move(lhs: RuleEntry, rhs: RuleEntry) -> None:
    if lhs.ruleset.name != rhs.ruleset.name:
        raise RestAPIRequestDataValidationException(
            title="Invalid rule move.", detail="The two rules are not in the same ruleset."
        )
    if lhs.rule.id == rhs.rule.id:
        raise RestAPIRequestDataValidationException(
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
def move_rule_to(param: Mapping[str, Any]) -> http.Response:
    """Move a rule to a specific location"""
    user.need_permission("wato.edit")
    user.need_permission("wato.rulesets")
    rule_id = param["rule_id"]

    body = param["body"]
    position = body["position"]

    source_entry = _get_rule_by_id(rule_id)
    if is_locked_by_quick_setup(source_entry.rule.locked_by):
        return problem(
            status=400,
            title="Rule is managed by Quick setup",
            detail="Rules managed by Quick setup cannot be moved.",
        )

    all_rulesets = source_entry.all_rulesets

    index: int
    dest_folder: Folder
    match position:
        case "top_of_folder":
            dest_folder = body["folder"]
            index = Ruleset.TOP
        case "bottom_of_folder":
            dest_folder = body["folder"]
            index = Ruleset.BOTTOM
        case "before_specific_rule":
            dest_entry = _get_rule_by_id(body["rule_id"], all_rulesets=all_rulesets)
            _validate_rule_move(source_entry, dest_entry)
            if is_locked_by_quick_setup(dest_entry.rule.locked_by):
                raise RestAPIRequestDataValidationException(
                    title="Invalid rule move.",
                    detail="Cannot move before a rule managed by Quick setup.",
                )
            index = dest_entry.index_nr
            dest_folder = dest_entry.folder
        case "after_specific_rule":
            dest_entry = _get_rule_by_id(body["rule_id"], all_rulesets=all_rulesets)
            _validate_rule_move(source_entry, dest_entry)
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
            return problem(
                status=400,
                title="Invalid position",
                detail=f"Position {position!r} is not a valid position.",
            )

    dest_folder.permissions.need_permission("write")
    source_entry.ruleset.move_to_folder(source_entry.rule, dest_folder, index)
    source_entry.folder = dest_folder
    all_rulesets.save(pprint_value=active_config.wato_pprint_config, debug=active_config.debug)
    affected_sites = source_entry.folder.all_site_ids()

    if dest_folder != source_entry.folder:
        affected_sites.extend(dest_folder.all_site_ids())

    add_change(
        action_name="edit-rule",
        text=_l('Changed properties of rule "%s", moved from folder "%s" to top of folder "%s"')
        % (source_entry.rule.id, source_entry.folder.title(), dest_folder.title()),
        user_id=user.id,
        sites=list(set(affected_sites)),
        object_ref=source_entry.rule.object_ref(),
        use_git=active_config.wato_use_git,
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
    value = body["value_raw"]
    ruleset_name = body["ruleset"]

    folder: Folder = body["folder"]
    folder.permissions.need_permission("write")

    rulesets = FolderRulesets.load_folder_rulesets(folder)
    ruleset = _retrieve_from_rulesets(rulesets, ruleset_name)

    try:
        _validate_value(ruleset, value)

    except FieldValidationException as exc:
        return problem(
            status=400,
            detail=exc.detail,
            title=exc.title,
        )

    rule = _create_rule(
        folder, ruleset, body.get("conditions", {}), body.get("properties", {}), value, gen_id()
    )

    index = ruleset.append_rule(folder, rule)
    rulesets.save_folder(pprint_value=active_config.wato_pprint_config, debug=active_config.debug)
    ruleset.add_new_rule_change(index, folder, rule)
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
    all_rulesets = AllRulesets.load_all_rulesets()
    ruleset_name = param["ruleset_name"]

    ruleset = _retrieve_from_rulesets(all_rulesets, ruleset_name)

    result = [
        _serialize_rule(
            RuleEntry(
                rule=rule,
                ruleset=rule.ruleset,
                folder=folder,
                index_nr=index,
                all_rulesets=all_rulesets,
            )
        )
        for folder, index, rule in ruleset.get_rules()
    ]

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


def _get_rule_by_id(rule_uuid: str, all_rulesets: AllRulesets | None = None) -> RuleEntry:
    if all_rulesets is None:
        all_rulesets = AllRulesets.load_all_rulesets()

    for ruleset in visible_rulesets(all_rulesets.get_rulesets()).values():
        folder: Folder
        index: int
        rule: Rule
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
        400: "The rule is locked and cannot be deleted.",
        404: "The rule to be deleted was not found.",
    },
    additional_status_codes=[
        204,
        400,
        404,
    ],
    permissions_required=RW_PERMISSIONS,
)
def delete_rule(param):
    """Delete a rule"""
    user.need_permission("wato.edit")
    user.need_permission("wato.rulesets")
    rule_id = param["rule_id"]
    rule: Rule
    all_rulesets = AllRulesets.load_all_rulesets()

    for ruleset in visible_rulesets(all_rulesets.get_rulesets()).values():
        for _folder, _index, rule in ruleset.get_rules():
            if rule.id == rule_id:
                if is_locked_by_quick_setup(rule.locked_by):
                    return problem(
                        status=400,
                        title="Rule is managed by Quick setup",
                        detail="Rules managed by Quick setup cannot be deleted.",
                    )
                ruleset.delete_rule(rule)
                all_rulesets.save(
                    pprint_value=active_config.wato_pprint_config, debug=active_config.debug
                )
                return http.Response(status=204)

    return problem(
        status=404,
        title="Rule not found.",
        detail=f"The rule with ID {rule_id!r} could not be found.",
    )


@Endpoint(
    constructors.object_href(domain_type="rule", obj_id="{rule_id}"),
    ".../update",
    method="put",
    etag="both",
    path_params=[RULE_ID],
    request_schema=UpdateRuleObject,
    response_schema=RuleObject,
    permissions_required=RW_PERMISSIONS,
)
def edit_rule(param):
    """Modify a rule"""
    user.need_permission("wato.edit")
    user.need_permission("wato.rulesets")
    body = param["body"]
    value = body["value_raw"]
    rule_entry = _get_rule_by_id(param["rule_id"])

    folder: Folder = rule_entry.folder
    folder.permissions.need_permission("write")

    ruleset = rule_entry.ruleset
    rulesets = rule_entry.all_rulesets
    current_rule = rule_entry.rule

    try:
        _validate_value(ruleset, value)

    except FieldValidationException as exc:
        return problem(
            status=400,
            detail=exc.detail,
            title=exc.title,
        )

    new_rule = _create_rule(
        folder,
        ruleset,
        body.get("conditions", {}),
        body.get("properties", {}),
        value,
        param["rule_id"],
    )

    if rule_entry.rule.conditions != new_rule.conditions:
        return problem(
            status=400,
            title="Rule is managed by Quick setup",
            detail="Conditions cannot be modified for rules managed by Quick setup.",
        )

    ruleset.edit_rule(current_rule, new_rule)
    rulesets.save_folder(
        folder, pprint_value=active_config.wato_pprint_config, debug=active_config.debug
    )

    new_rule_entry = _get_rule_by_id(param["rule_id"])
    return serve_json(_serialize_rule(new_rule_entry))


def _validate_value(ruleset: Ruleset, value: Any) -> None:
    try:
        valuespec = ruleset.valuespec()
        valuespec.validate_datatype(value, "")
        valuespec.validate_value(value, "")

    except exceptions.MKUserError as exc:
        if exc.varname is None:
            title = "A field has a problem"
        else:
            field_name = strip_tags(exc.varname.replace("_p_", ""))
            title = f"Problem in (sub-)field {field_name!r}"

        exception = FieldValidationException()
        exception.title = title
        exception.detail = strip_tags(exc.message)
        raise exception


def _api_to_internal(
    api_label_group_conditions: list[APILabelGroupCondition] | None,
) -> LabelGroups | None:
    """
    >>> _api_to_internal([{"operator": "and", "label_group": [{"operator": "and", "label": "os:windows"}]}])
    [('and', [('and', 'os:windows')])]
    """
    if api_label_group_conditions is None:
        return None

    internal_label_groups: LabelGroups = [
        (
            label_group_condition["operator"],
            [
                (label_condition["operator"], label_condition["label"])
                for label_condition in label_group_condition["label_group"]
            ],
        )
        for label_group_condition in api_label_group_conditions
    ]

    return internal_label_groups


def _internal_to_api(label_groups: LabelGroups | None) -> list[APILabelGroupCondition] | None:
    """
    >>> _internal_to_api([("and", [("and", "os:windows")])])
    [{'operator': 'and', 'label_group': [{'operator': 'and', 'label': 'os:windows'}]}]
    """

    if label_groups is None:
        return None

    api_label_group_conditions: list[APILabelGroupCondition] = [
        {
            "operator": group_op,
            "label_group": [{"operator": op, "label": label} for op, label in label_group],
        }
        for group_op, label_group in label_groups
    ]
    return api_label_group_conditions


def _create_rule(
    folder: Folder,
    ruleset: Ruleset,
    conditions: dict[str, Any],
    properties: RuleOptionsSpec,
    value: Any,
    rule_id: str = gen_id(),
) -> Rule:
    rule = Rule(
        rule_id,
        folder,
        ruleset,
        RuleConditions(
            host_folder=folder.path(),
            host_tags=conditions.get("host_tags"),
            host_label_groups=(
                _api_to_internal(conditions.get("host_label_groups"))
                if allow_host_label_conditions(ruleset.rulespec.name)
                else None
            ),
            host_name=conditions.get("host_name"),
            service_description=(
                conditions.get("service_description") if ruleset.item_type() else None
            ),
            service_label_groups=(
                _api_to_internal(conditions.get("service_label_groups"))
                if (ruleset.item_type() and allow_service_label_conditions(ruleset.rulespec.name))
                else None
            ),
        ),
        RuleOptions.from_config(properties),
        ruleset.valuespec().transform_value(value),
    )

    return rule


def _retrieve_from_rulesets(rulesets: RulesetCollection, ruleset_name: str) -> Ruleset:
    ruleset_exception = ProblemException(
        status=400,
        title="Unknown ruleset.",
        detail=f"The ruleset of name {ruleset_name!r} is not known.",
    )
    try:
        ruleset = rulesets.get(ruleset_name)
    except KeyError:
        raise ruleset_exception

    if not visible_ruleset(ruleset.rulespec.name):
        raise ruleset_exception

    return ruleset


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
                    "host_label_groups": _internal_to_api(rule.conditions.host_label_groups),
                    "service_description": rule.conditions.service_description,
                    "service_label_groups": _internal_to_api(rule.conditions.service_label_groups),
                }
            ),
        },
    )


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(move_rule_to, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(create_rule, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(list_rules, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show_rule, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete_rule, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(edit_rule, ignore_duplicates=ignore_duplicates)
