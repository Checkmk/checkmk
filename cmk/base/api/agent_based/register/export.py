#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""All objects defined here are intended to be exposed in the API
"""
from typing import (  # pylint: disable=unused-import
    Optional, List,
)
from cmk.base import config

from cmk.base.api.agent_based.section_types import (  # pylint: disable=unused-import
    AgentParseFunction, HostLabelFunction, SNMPDetectSpec, SNMPParseFunction, SNMPTree,
)
from cmk.base.api.agent_based.register.section_plugins import (
    create_agent_section_plugin,
    create_snmp_section_plugin,
)


def agent_section(
        #*,
        name=None,  # type: Optional[str]
        parsed_section_name=None,  # type: Optional[str]
        parse_function=None,  # type: Optional[AgentParseFunction]
        host_label_function=None,  # type: Optional[HostLabelFunction]
        supersedes=None,  # type: Optional[List[str]]
):
    # type: (...) -> None
    """Register an agent section to checkmk

    The section marked by '<<<name>>>' in the raw agent output will be processed
    according to the functions and options given to this function:

    :param name: The name of the section to be processed. It must be unique, and match
        the section header of the agent oufput ('<<<name>>>').
    :params parsed_section_name: not yet implemented.
    :params parse_function: The function responsible for parsing the raw agent data.
        It must accept exactly one argument by the name 'string_table'.
        It may return an arbitrary object. Note that if the return value is falsey,
        no forther processing will take place.
    :params host_label_function: The function responsible for extracting HostLabels from
        the parsed data. It must accept exactly one argument by the name 'section'. When
        the function is called, it will be passed the parsed data as returned by the
        parse function. It is expected to yield objects of type 'HostLabel'.
    :params supersedes: not yet implemented.
    """
    # TODO (mo): unhack this CMK-3983
    if name is None or parse_function is None:
        raise TypeError()

    forbidden_names = list(config.registered_agent_sections) + list(config.registered_snmp_sections)

    section_plugin = create_agent_section_plugin(
        name=name,
        parsed_section_name=parsed_section_name,
        parse_function=parse_function,
        host_label_function=host_label_function,
        supersedes=supersedes,
        forbidden_names=forbidden_names,
    )

    config.registered_agent_sections[section_plugin.name] = section_plugin


def snmp_section(
        #*,
        name=None,  # type: Optional[str]
        parsed_section_name=None,  # type: Optional[str]
        parse_function=None,  # type: Optional[SNMPParseFunction]
        host_label_function=None,  # type: Optional[HostLabelFunction]
        detect=None,  # type: Optional[SNMPDetectSpec]
        trees=None,  # type: Optional[List[SNMPTree]]
        supersedes=None,  # type: Optional[List[str]]
):
    # type: (...) -> None
    """Register an snmp section to checkmk

    The snmp information will be gathered and parsed according to the functions and
    options given to this function:

    :param name: The name of the section to be processed. It must be unique, and match
        the section header of the agent oufput ('<<<name>>>').
    :params parsed_section_name: not yet implemented.
    :params parse_function: The function responsible for parsing the raw snmp data.
        It must accept exactly one argument by the name 'string_table'.
        It may return an arbitrary object. Note that if the return value is falsey,
        no forther processing will take place.
    :params host_label_function: The function responsible for extracting HostLabels from
        the parsed data. It must accept exactly one argument by the name 'section'. When
        the function is called, it will be passed the parsed data as returned by the
        parse function. It is expected to yield objects of type 'HostLabel'.
    :params detect: The conditions on single OIDs that will result in the attempt to
        fetch snmp data and discover services. This should only match devices to which
        the section is applicable.
    :params trees: The specification of snmp data that should be fetched from the device.
        It must be a list of SNMPTree objects. The parse function will be passed a list of
        one SNMP table per specified Tree, where an SNMP tree is a list of lists of strings.
    :params supersedes: not yet implemented.
    """
    # TODO (mo): unhack this CMK-3983
    if name is None or parse_function is None or detect is None or trees is None:
        raise TypeError("missing argument: name, parse_function, detect or trees")

    forbidden_names = list(config.registered_agent_sections) + list(config.registered_snmp_sections)

    section_plugin = create_snmp_section_plugin(
        name=name,
        parsed_section_name=parsed_section_name,
        parse_function=parse_function,
        host_label_function=host_label_function,
        detect_spec=detect,
        trees=trees,
        supersedes=supersedes,
        forbidden_names=forbidden_names,
    )

    config.registered_snmp_sections[section_plugin.name] = section_plugin


__all__ = ["agent_section", "snmp_section"]
