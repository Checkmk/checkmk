#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable, List, Optional, Set, Tuple

import inspect
from pathlib import Path

from cmk.utils.type_defs import ParsedSectionName, SectionName

from cmk.base.api.agent_based.type_defs import SectionPlugin


def get_plugin_module_name() -> Optional[str]:
    """find out which module registered the plugin"""
    try:
        calling_from = inspect.stack()[2].filename
    except UnicodeDecodeError:  # calling from precompiled host file
        return None
    return Path(calling_from).stem


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
