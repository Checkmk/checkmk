#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""All objects defined here are intended to be exposed in the API
"""
from typing import Any, Callable, Dict, List, Optional

from cmk.snmplib.type_defs import SNMPDetectSpec, SNMPTree

from cmk.base import config
from cmk.base.api.agent_based.checking_types import CheckFunction, DiscoveryFunction
from cmk.base.api.agent_based.register.check_plugins import create_check_plugin
from cmk.base.api.agent_based.register.section_plugins import (
    create_agent_section_plugin,
    create_snmp_section_plugin,
)
from cmk.base.api.agent_based.section_types import (
    AgentParseFunction,
    HostLabelFunction,
    SNMPParseFunction,
)


def agent_section(
    *,
    name: str,
    parsed_section_name: Optional[str] = None,
    parse_function: AgentParseFunction,
    host_label_function: Optional[HostLabelFunction] = None,
    supersedes: Optional[List[str]] = None,
) -> None:
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
    *,
    name: str,
    parsed_section_name: Optional[str] = None,
    parse_function: SNMPParseFunction,
    host_label_function: Optional[HostLabelFunction] = None,
    detect: SNMPDetectSpec,
    trees: List[SNMPTree],
    supersedes: Optional[List[str]] = None,
) -> None:
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


def check_plugin(
    *,
    name: str,
    sections: Optional[List[str]] = None,
    service_name: str,
    discovery_function: DiscoveryFunction,
    discovery_default_parameters: Optional[Dict[str, Any]] = None,
    discovery_ruleset_name: Optional[str] = None,
    check_function: CheckFunction,
    check_default_parameters: Optional[Dict[str, Any]] = None,
    check_ruleset_name: Optional[str] = None,
    cluster_check_function: Optional[Callable] = None,
) -> None:
    """Register a check plugin to checkmk.

    :param name: The name of the check plugin. It must be unique. And contain only the characters
                 A-Z, a-z, 0-9 and the underscore.
    :param sections: An optional list of section names that this plugin subscribes to. The
                     corresponding sections are passed to the discovery and check function. The
                     functions arguments must be called 'section_<name1>, section_<name2>' ect.
                     Default: [<name>]
    :param service_name: The template for the service. The check function must accept 'item' as
                         first argument if and only if "%s" is present in the value of
                         "service_name".
    :param discovery_function: The discovery_function. Arguments must be 'params' (if discovery
                               parameters are defined) and 'section_<name1>, section_<name2>' ect.
                               corresponding to the `sections`.
    :param discovery_parameters: Default parameters for the discovery function. Must match the
                                 ValueSpec of the corresponding WATO ruleset.
    :param discovery_ruleset_name: The name of the discovery ruleset.
    :param check_function: The check_function. Arguments must be 'item' (if the service has an item)
                           'params' (if check parameters are defined) and 'section_<name1>,
                           section_<name2>' ect. corresponding to the `sections`.
    :param check_parameters: Default parameters for the check function. Must match the
                             ValueSpec of the corresponding WATO ruleset.
    :param check_ruleset_name: The name of the check ruleset.
    """
    plugin = create_check_plugin(
        name=name,
        sections=sections,
        service_name=service_name,
        discovery_function=discovery_function,
        discovery_default_parameters=discovery_default_parameters,
        discovery_ruleset_name=discovery_ruleset_name,
        check_function=check_function,
        check_default_parameters=check_default_parameters,
        check_ruleset_name=check_ruleset_name,
        cluster_check_function=cluster_check_function,
        forbidden_names=list(config.registered_check_plugins),
    )

    config.registered_check_plugins[plugin.name] = plugin


__all__ = [
    "agent_section",
    "check_plugin",
    "snmp_section",
]
