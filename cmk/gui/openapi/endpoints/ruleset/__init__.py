#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Rulesets"""

from __future__ import annotations

from cmk.gui.config import active_config
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.ruleset.fields import (
    RULESET_NAME,
    RulesetCollection,
    RulesetObject,
    RulesetSearchOptions,
)
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.openapi.utils import problem, serve_json
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.utils.escaping import strip_tags
from cmk.gui.watolib.rulesets import (
    AllRulesets,
    FolderRulesets,
    Ruleset,
    SingleRulesetRecursively,
    visible_ruleset,
    visible_rulesets,
)
from cmk.gui.watolib.rulesets import RulesetCollection as RulesetCollection_

LIST_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.rulesets"),
        permissions.Optional(permissions.Perm("wato.edit_all_passwords")),
    ]
)
PERMISSIONS = permissions.Perm("wato.rulesets")


@Endpoint(
    constructors.collection_href(domain_type="ruleset"),
    ".../collection",
    method="get",
    query_params=[RulesetSearchOptions],
    response_schema=RulesetCollection,
    permissions_required=LIST_PERMISSIONS,
)
def list_rulesets(param):
    """Search rule sets"""
    user.need_permission("wato.rulesets")
    all_sets = (
        FolderRulesets.load_folder_rulesets(param["folder"])
        if param.get("folder")
        else AllRulesets.load_all_rulesets()
    )

    def _get_search_options(params):
        # We remove 'folder' because that has already been handled at the start of the endpoint.
        options = dict(params)
        if "folder" in options:
            del options["folder"]
        return options

    if search_options := _get_search_options(param):
        rulesets = RulesetCollection_(
            {
                name: ruleset
                for name, ruleset in all_sets.get_rulesets().items()
                if ruleset.matches_search_with_rules(search_options, debug=active_config.debug)
            }
        )
    else:
        rulesets = all_sets

    # We don't do grouping like in the GUI. This would not add any value here.
    return serve_json(
        constructors.collection_object(
            domain_type="ruleset",
            value=[
                _serialize_ruleset(ruleset)
                for ruleset in visible_rulesets(rulesets.get_rulesets()).values()
            ],
        )
    )


@Endpoint(
    constructors.object_href(domain_type="ruleset", obj_id="{ruleset_name}"),
    "cmk/show",
    method="get",
    etag="output",
    path_params=[RULESET_NAME],
    response_schema=RulesetObject,
    permissions_required=PERMISSIONS,
)
def show_ruleset(param):
    """Show a ruleset"""
    ruleset_name = param["ruleset_name"]
    user.need_permission("wato.rulesets")

    ruleset_problem = problem(
        title="Unknown ruleset.",
        detail=f"The ruleset of name {ruleset_name!r} is not known.",
        status=404,
    )
    try:
        ruleset = SingleRulesetRecursively.load_single_ruleset_recursively(ruleset_name).get(
            ruleset_name
        )
    except KeyError:
        return ruleset_problem

    if not visible_ruleset(ruleset.rulespec.name):
        return ruleset_problem

    return serve_json(_serialize_ruleset(ruleset))


def _serialize_ruleset(ruleset: Ruleset) -> DomainObject:
    members = {}
    if ruleset.num_rules() > 0:
        members["rules"] = constructors.collection_property(
            name="rules",
            value=[],
            base="",
        )

    return constructors.domain_object(
        domain_type="ruleset",
        identifier=ruleset.name,
        title=ruleset.title() or ruleset.name,
        editable=False,
        deletable=False,
        members=members,
        extensions={
            "name": ruleset.name,
            "title": ruleset.title(),
            "item_type": ruleset.item_type(),
            "item_name": ruleset.item_name(),
            "item_enum": ruleset.item_enum(),
            "match_type": ruleset.match_type(),
            "help": strip_tags(ruleset.help()),
            "number_of_rules": ruleset.num_rules(),
        },
    )


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(list_rulesets, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show_ruleset, ignore_duplicates=ignore_duplicates)
