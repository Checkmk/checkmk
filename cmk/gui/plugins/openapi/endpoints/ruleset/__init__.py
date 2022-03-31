#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Rulesets"""
from __future__ import annotations

from typing import List

from cmk.gui import watolib
from cmk.gui.plugins.openapi.endpoints.ruleset.fields import (
    RULESET_NAME,
    RulesetCollection,
    RulesetObject,
    RulesetSearchOptions,
)
from cmk.gui.plugins.openapi.restful_objects import constructors, Endpoint, permissions
from cmk.gui.plugins.openapi.restful_objects.constructors import serve_json
from cmk.gui.plugins.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.utils.escaping import strip_tags
from cmk.gui.utils.logged_in import user

PERMISSIONS = permissions.Perm("wato.rulesets")


@Endpoint(
    constructors.collection_href(domain_type="ruleset"),
    ".../collection",
    method="get",
    query_params=[RulesetSearchOptions],
    response_schema=RulesetCollection,
    permissions_required=PERMISSIONS,
)
def list_rulesets(param):
    """Search rule sets"""
    user.need_permission("wato.rulesets")
    all_sets = (
        watolib.FolderRulesets(param["folder"]) if param.get("folder") else watolib.AllRulesets()
    )
    all_sets.load()

    def _get_search_options(params):
        # We remove 'folder' because that has already been handled at the start of the endpoint.
        options = dict(params)
        if "folder" in options:
            del options["folder"]
        return options

    if search_options := _get_search_options(param):
        all_sets = watolib.SearchedRulesets(all_sets, search_options)

    ruleset_collection: List[DomainObject] = []
    for ruleset in all_sets.get_rulesets().values():
        ruleset_collection.append(_serialize_ruleset(ruleset))

    # We don't do grouping like in the GUI. This would not add any value here.
    return serve_json(
        constructors.collection_object(
            domain_type="ruleset",
            value=ruleset_collection,
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
    collection = watolib.SingleRulesetRecursively(ruleset_name)
    collection.load()
    ruleset = collection.get(ruleset_name)
    return serve_json(_serialize_ruleset(ruleset))


def _serialize_ruleset(ruleset: watolib.Ruleset) -> DomainObject:
    members = {}
    if ruleset.num_rules() > 0:
        members["rules"] = constructors.collection_property(
            name="rules",
            value=[],
            base="",
        )

    return constructors.domain_object(
        domain_type="ruleset",
        identifier=ruleset.name.replace(":", "-"),
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
