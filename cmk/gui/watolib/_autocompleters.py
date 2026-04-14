#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Autocompleters that depend on watolib modules."""

# mypy: disable-error-code="type-arg"

from typing import get_args

from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.groups import GroupType
from cmk.gui.i18n import _
from cmk.gui.type_defs import Choices
from cmk.gui.watolib.check_mk_automations import get_check_information_cached
from cmk.gui.watolib.groups_io import all_groups


def _matches_id_or_title(ident: str, choice: tuple[str | None, str]) -> bool:
    return ident.lower() in (choice[0] or "").lower() or ident.lower() in choice[1].lower()


def hostgroup_autocompleter(config: Config, value: str, params: dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get
    the list of choices
    """
    group_type = params["group_type"]
    if group_type not in (valid_group_types := get_args(GroupType)):
        raise MKUserError(
            "params",
            _("you need to set %s parameter to either %s.")
            % ("group_type", str(valid_group_types)),
        )
    choices: Choices = sorted(
        (v for v in all_groups(group_type) if _matches_id_or_title(value, v)),
        key=lambda a: a[1].lower(),
    )
    if not params.get("strict"):
        empty_choice: Choices = [("", "")]
        choices = empty_choice + choices
    return choices


def tag_group_autocompleter(config: Config, value: str, params: dict) -> Choices:
    return sorted(
        (v for v in config.tags.get_tag_group_choices() if _matches_id_or_title(value, v)),
        key=lambda a: a[1].lower(),
    )


def tag_group_opt_autocompleter(config: Config, value: str, params: dict) -> Choices:
    grouped: Choices = []

    for tag_group in config.tags.tag_groups:
        if tag_group.id == params["group_id"]:
            grouped.append(("", ""))
            for grouped_tag in tag_group.tags:
                tag_id = "" if grouped_tag.id is None else grouped_tag.id
                if value.lower() in grouped_tag.title.lower() or value == grouped_tag.id:
                    grouped.append((tag_id, grouped_tag.title))
    return grouped


def check_types_autocompleter(config: Config, value: str, params: dict) -> Choices:
    return [
        (str(cn), (str(cn) + " - " + c["title"]))
        for (cn, c) in get_check_information_cached(debug=config.debug).items()
        if not cn.is_management_name()
    ]
