#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple, Union

import inspect

from pathlib import Path

from cmk.utils.type_defs import CheckPluginName, InventoryPluginName, ParsedSectionName, SectionName
from cmk.utils.paths import agent_based_plugins_dir

from cmk.base.api.agent_based.type_defs import SectionPlugin


def get_validated_plugin_module_name() -> Optional[str]:
    """Find out which module registered the plugin and make sure its in the right place"""
    try:
        calling_from = inspect.stack()[2].filename
    except UnicodeDecodeError:  # calling from precompiled host file
        return None

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
    func_type: str,
    function: Callable,
    has_item: bool,
    has_params: bool,
    sections: List[ParsedSectionName],
) -> None:
    """Validate the functions signature and type"""

    if not inspect.isgeneratorfunction(function):
        raise TypeError("%s function must be a generator function" % (func_type,))

    expected_params = []
    if has_item:
        expected_params.append('item')
    if has_params:
        expected_params.append('params')
    if len(sections) == 1:
        expected_params.append('section')
    else:
        expected_params.extend('section_%s' % s for s in sections)

    if expected_params != list(inspect.signature(function).parameters):
        raise TypeError("%s function: expected function arguments: %s" %
                        (func_type, ', '.join(expected_params)))


def validate_default_parameters(
    params_type: str,
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
