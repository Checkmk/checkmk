#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Generator, Sequence, Tuple

import pytest  # type: ignore[import]

from cmk.utils.type_defs import ParsedSectionName
import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.api.agent_based.type_defs import SectionPlugin, SNMPSectionPlugin


def _section_permutations(
    parsed_section_names: Sequence[ParsedSectionName],
) -> Generator[Tuple[SectionPlugin, ...], None, None]:

    if not parsed_section_names:
        yield ()
        return

    if len(parsed_section_names) >= 1:
        for section_name in agent_based_register.get_section_producers(parsed_section_names[0]):
            for perm in _section_permutations(parsed_section_names[1:]):
                yield (agent_based_register.get_section_plugin(section_name),) + perm


def _get_empty_parsed_result(section: SectionPlugin) -> object:
    return section.parse_function(len(section.trees) * [[]]  # type: ignore[arg-type]
                                 ) if isinstance(section, SNMPSectionPlugin) else None


@pytest.mark.usefixtures("config_load_all_checks")
def test_check_plugins_do_not_discover_upon_empty_snmp_input():
    """
    In Checkmk < 1.6 the parse function has not been called for empty table data,
    unless "handle_empty_info" has been set.

    From version 2.0 on, the parse function will be called allways.
    In case no further processing is desired, the parse functions should return `None`.

    (Returning something falsey usually means nothing will be discovered!)

    Since this was the behaviour for *almost* every plugin we maintain this test
    with a list of known exceptions, to ensure the old behaviour is not changed.

    However: There is nothing wrong with not returning None, in principle.
    If you whish to do that (see one of the listed exeptions for examples),
    just add an exception below. If maintaining this test becvomes too tedious,
    we can probably just remove it.
    """

    plugins_expected_to_discover_upon_empty = {
        "printer_alerts",
        "liebert_system_events",
        "apc_inrow_system_events",
    }

    plugins_discovering_upon_empty = set()
    for plugin in agent_based_register.iter_all_check_plugins():
        for sections in _section_permutations(plugin.sections):
            kwargs = {str(section.name): _get_empty_parsed_result(section) for section in sections}
            if all(v is None for v in kwargs.values()):
                continue

            if len(kwargs) > 1:
                kwargs = {f"section_{k}": v for k, v in kwargs.items()}
            else:
                kwargs = {"section": v for v in kwargs.values()}

            if plugin.discovery_default_parameters is not None:
                kwargs["params"] = plugin.discovery_default_parameters if (
                    plugin.discovery_ruleset_type
                    == "merged") else [plugin.discovery_default_parameters]

            if list(plugin.discovery_function(**kwargs)):
                plugins_discovering_upon_empty.add(str(plugin.name))

    assert plugins_discovering_upon_empty == plugins_expected_to_discover_upon_empty
