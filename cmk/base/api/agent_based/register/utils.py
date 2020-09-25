#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from typing import Callable, Dict, Iterable, List, Literal, Optional, Set, Tuple, Union

import inspect

from pathlib import Path

from cmk.utils.type_defs import (CheckPluginName, InventoryPluginName, ParsedSectionName,
                                 SectionName, RuleSetName)
from cmk.utils.paths import agent_based_plugins_dir

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import SectionPlugin

ITEM_VARIABLE = "%s"

DUMMY_RULESET_NAME = "non_existent_auto_migration_dummy_rule"


def get_validated_plugin_module_name() -> Optional[str]:
    """Find out which module registered the plugin and make sure its in the right place"""
    # We used this before, but it was a performance killer. The method below is a lot faster.
    # calling_from = inspect.stack()[2].filename
    frame = sys._getframe(2)
    if not frame:
        return None
    calling_from = frame.f_code.co_filename

    path = Path(calling_from)
    if not path.parent.parts[-3:] == agent_based_plugins_dir.parts[-3:]:
        raise ImportError("do not register from %r" % path)

    return path.stem


def rank_sections_by_supersedes(
    available_raw_section_definitions: Iterable[Tuple[SectionName, SectionPlugin]],
    filter_parsed_sections: Optional[Set[ParsedSectionName]],
) -> List[SectionPlugin]:
    """Get the raw sections that will be parsed into the required section

    Raw sections may get renamed once they are parsed, if they declare it. This function
    deals with the task of determining which sections we need to parse, in order to end
    up with the desired parsed section.

    They are ranked according to their supersedings.
    """
    candidates = dict(available_raw_section_definitions) if filter_parsed_sections is None else {
        name: section
        for name, section in available_raw_section_definitions
        if section.parsed_section_name in filter_parsed_sections
    }

    # Validation has enforced that we have no implizit (recursive) supersedings.
    # This has the advantage, that we can just sort by number of relevant supersedings.
    candidate_names = set(candidates)

    def _count_relevant_supersedings(section: SectionPlugin):
        return -len(section.supersedes & candidate_names), section.name

    return sorted(candidates.values(), key=_count_relevant_supersedings)


def create_subscribed_sections(
    sections: Optional[List[str]],
    plugin_name: Union[InventoryPluginName, CheckPluginName],
) -> List[ParsedSectionName]:
    if sections is None:
        return [ParsedSectionName(str(plugin_name))]
    if not isinstance(sections, list):
        raise TypeError("'sections' must be a list of str, got %r" % (sections,))
    if not sections:
        raise ValueError("'sections' must not be empty")
    return [ParsedSectionName(n) for n in sections]


def validate_function_arguments(
    *,
    type_label: Literal["check", "cluster_check", "discovery", "host_label", "inventory"],
    function: Callable,
    has_item: bool,
    default_params: Optional[Dict],
    sections: List[ParsedSectionName],
) -> None:
    """Validate the functions signature and type"""

    if not inspect.isgeneratorfunction(function):
        raise TypeError(f"{type_label}_function must be a generator function")

    expected_params = []
    if has_item:
        expected_params.append('item')
    if default_params is not None:
        expected_params.append('params')
    if len(sections) == 1:
        expected_params.append('section')
    else:
        expected_params.extend('section_%s' % s for s in sections)

    present_params = list(inspect.signature(function).parameters)

    if expected_params == present_params:
        return

    # We know we must raise. Dispatch for a better error message:

    if set(expected_params) == set(present_params):  # not len()!
        exp_str = ', '.join(expected_params)
        raise TypeError(f"{type_label}_function: wrong order of arguments. Expected: {exp_str}")

    symm_diff = set(expected_params).symmetric_difference(present_params)

    if "item" in symm_diff:
        missing_or_unexpected = "missing" if has_item else "unexpected"
        raise TypeError(f"{type_label}_function: {missing_or_unexpected} 'item' argument")

    if "params" in symm_diff:
        raise TypeError(f"{type_label}_function: 'params' argument expected if "
                        "and only if default parameters are not None")

    exp_str = ', '.join(expected_params)
    raise TypeError(f"{type_label}_function: expected arguments: {exp_str}")


def validate_default_parameters(
    params_type: Literal["check", "discovery", "inventory"],
    ruleset_name: Optional[str],
    default_parameters: Optional[Dict],
) -> None:
    if default_parameters is None:
        if ruleset_name is None:
            return
        raise TypeError("missing default %s parameters for ruleset %s" %
                        (params_type, ruleset_name))

    if not isinstance(default_parameters, dict):
        raise TypeError("default %s parameters must be dict" % (params_type,))

    if ruleset_name is None and params_type != 'check':
        raise TypeError("missing ruleset name for default %s parameters" % (params_type))


def validate_check_ruleset_item_consistency(
    check_plugin: CheckPlugin,
    check_plugins_by_ruleset_name: Dict[Optional[RuleSetName], List[CheckPlugin]],
) -> None:
    """Validate check plugins sharing a check_ruleset_name have either all or none an item.

    Mixed checkgroups lead to strange exceptions when processing the check parameters.
    So it is much better to catch these errors in a central place with a clear error message.
    """
    if (check_plugin.check_ruleset_name is None or
            str(check_plugin.check_ruleset_name) == DUMMY_RULESET_NAME):
        return

    present_check_plugins = check_plugins_by_ruleset_name[check_plugin.check_ruleset_name]
    if not present_check_plugins:
        return

    # Trying to detect whether or not the check has an item. But this mechanism is not
    # 100% reliable since Checkmk appends an item to the service_description when "%s"
    # is not in the checks service_description template.
    # Maybe we need to define a new rule which enforces the developer to use the %s in
    # the service_description. At least for grouped checks.
    item_present = ITEM_VARIABLE in check_plugin.service_name
    item_expected = ITEM_VARIABLE in present_check_plugins[0].service_name

    if item_present is not item_expected:
        present_plugins = ", ".join(str(p.name) for p in present_check_plugins)
        raise ValueError(
            f"Check ruleset {check_plugin.check_ruleset_name} has checks with and without item! "
            "At least one of the checks in this group needs to be changed "
            f"(offending plugin: {check_plugin.name}, present_plugins: {present_plugins}).")
