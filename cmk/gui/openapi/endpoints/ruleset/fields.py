#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from cmk.gui import fields as gui_fields
from cmk.gui.fields import base
from cmk.gui.openapi.restful_objects import response_schemas

from cmk import fields

RULESET_NAME = {
    "ruleset_name": fields.String(
        description="The name of the ruleset.",
        example="host_groups",
        required=True,
    )
}


class RulesetExtensions(base.BaseSchema):
    name = fields.String(
        description="The name of the ruleset",
        example="host_groups",
    )
    folder = gui_fields.FolderField(required=True, example="~router")
    number_of_rules = fields.Integer(
        description="The number of rules of this ruleset.",
        example=5,
    )


class RulesetObject(response_schemas.DomainObject):
    domainType = fields.Constant(
        "ruleset",
        description="Domain type of this object.",
        example="ruleset",
    )
    extensions = fields.Nested(
        RulesetExtensions,
        description="Specific attributes related to rulesets.",
    )


class RulesetCollection(response_schemas.DomainObjectCollection):
    domainType = fields.Constant(
        "ruleset",
        description="Domain type of this object.",
        example="ruleset",
    )


class RulesetSearchOptions(base.BaseSchema):
    """

    search_options = {
        "fulltext": None,
        "ruleset_deprecated": False,
        "ruleset_used": False,
        "ruleset_name": False,
        "ruleset_title": False,
        "ruleset_help": False,
    }

    """

    cast_to_dict = True

    fulltext = fields.String(
        description=(
            "Search all keys (like `name`, `title`, `help`, etc.) for this text. Regex allowed."
        ),
        example="name",
    )
    folder = gui_fields.FolderField(
        description="The folder in which to search for rules.", example="~"
    )
    deprecated = fields.Boolean(
        attribute="ruleset_deprecated",
        description="Only show deprecated rulesets. Defaults to False.",
        example=False,
        load_default=False,
    )
    used = fields.Boolean(
        attribute="ruleset_used",
        description="Only show used rulesets. Defaults to True.",
        example=True,
        load_default=True,
    )
    name = fields.String(
        attribute="ruleset_name", description="A regex of the name.", example="Some regex"
    )
