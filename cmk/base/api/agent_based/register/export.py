#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""All objects defined here are intended to be exposed in the API
"""
from typing import Callable, List, Optional, overload, Union

from cmk.base.api.agent_based.checking_classes import CheckFunction, DiscoveryFunction
from cmk.base.api.agent_based.inventory_classes import InventoryFunction
from cmk.base.api.agent_based.register import (
    add_check_plugin,
    add_discovery_ruleset,
    add_inventory_plugin,
    add_section_plugin,
    is_registered_check_plugin,
    is_registered_inventory_plugin,
    is_registered_section_plugin,
)
from cmk.base.api.agent_based.register.check_plugins import create_check_plugin
from cmk.base.api.agent_based.register.inventory_plugins import create_inventory_plugin
from cmk.base.api.agent_based.register.section_plugins import (
    create_agent_section_plugin,
    create_snmp_section_plugin,
)
from cmk.base.api.agent_based.register.utils import get_validated_plugin_module_name, RuleSetType
from cmk.base.api.agent_based.section_classes import SNMPDetectSpecification, SNMPTree
from cmk.base.api.agent_based.type_defs import (
    AgentParseFunction,
    HostLabelFunction,
    ParametersTypeAlias,
    SimpleSNMPParseFunction,
    SNMPParseFunction,
)

__all__ = [
    "agent_section",
    "snmp_section",
    "check_plugin",
    "inventory_plugin",
    "RuleSetType",
]


def agent_section(
    *,
    name: str,
    parse_function: Optional[AgentParseFunction] = None,
    parsed_section_name: Optional[str] = None,
    host_label_function: Optional[HostLabelFunction] = None,
    host_label_default_parameters: Optional[ParametersTypeAlias] = None,
    host_label_ruleset_name: Optional[str] = None,
    host_label_ruleset_type: RuleSetType = RuleSetType.MERGED,
    supersedes: Optional[List[str]] = None,
) -> None:
    """Register an agent section to checkmk

    The section marked by '<<<name>>>' in the raw agent output will be processed
    according to the functions and options given to this function:

    Args:

      name:                The unique name of the section to be registered.
                           It must match the section header of the agent output ('<<<name>>>').

      parse_function:      The function responsible for parsing the raw agent data.
                           It must accept exactly one argument by the name 'string_table'.
                           It may return an arbitrary object. Note that if the return value is
                           `None`, no forther processing will take place (just as if the agent had
                           not sent any data).
                           This function may raise arbitrary exceptions, which will be dealt with
                           by the checking engine. You should expect well formatted data.

      parsed_section_name: The name under which the parsed section will be available to the plugins.
                           Defaults to the original name.

      host_label_function: The function responsible for extracting host labels from the parsed data.
                           It must accept exactly one argument by the name 'section'.
                           When the function is called, it will be passed the parsed data as
                           returned by the parse function.
                           It is expected to yield objects of type :class:`HostLabel`.

      host_label_default_parameters: Default parameters for the host label function. Must match
                           the ValueSpec of the corresponding WATO ruleset, if it exists.

      host_label_ruleset_name: The name of the host label ruleset.

      host_label_ruleset_type: The ruleset type is either :class:`RuleSetType.ALL` or
                           :class:`RuleSetType.MERGED`.
                           It describes whether this plugins needs the merged result of the
                           effective rules, or every individual rule matching for the current host.

      supersedes:          A list of section names which are superseded by this sections. If this
                           section will be parsed to something that is not `None` (see above) all
                           superseded section will not be considered at all.

    """
    section_plugin = create_agent_section_plugin(
        name=name,
        parsed_section_name=parsed_section_name,
        parse_function=parse_function,
        host_label_function=host_label_function,
        host_label_default_parameters=host_label_default_parameters,
        host_label_ruleset_name=host_label_ruleset_name,
        host_label_ruleset_type=host_label_ruleset_type,
        supersedes=supersedes,
        module=get_validated_plugin_module_name(),
    )

    if is_registered_section_plugin(section_plugin.name):
        raise ValueError("duplicate section definition: %s" % section_plugin.name)

    add_section_plugin(section_plugin)


@overload  # no List of trees -> SimpleSNMPParseFunction
def snmp_section(
    *,
    name: str,
    detect: SNMPDetectSpecification,
    fetch: SNMPTree,
    parse_function: Optional[SimpleSNMPParseFunction] = None,
    parsed_section_name: Optional[str] = None,
    host_label_function: Optional[HostLabelFunction] = None,
    host_label_default_parameters: Optional[ParametersTypeAlias] = None,
    host_label_ruleset_name: Optional[str] = None,
    host_label_ruleset_type: RuleSetType = RuleSetType.MERGED,
    supersedes: Optional[List[str]] = None,
) -> None:
    pass


@overload
def snmp_section(
    *,
    name: str,
    detect: SNMPDetectSpecification,
    fetch: List[SNMPTree],
    parse_function: Optional[SNMPParseFunction] = None,
    parsed_section_name: Optional[str] = None,
    host_label_function: Optional[HostLabelFunction] = None,
    host_label_default_parameters: Optional[ParametersTypeAlias] = None,
    host_label_ruleset_name: Optional[str] = None,
    host_label_ruleset_type: RuleSetType = RuleSetType.MERGED,
    supersedes: Optional[List[str]] = None,
) -> None:
    pass


def snmp_section(
    *,
    name: str,
    detect: SNMPDetectSpecification,
    fetch: Union[SNMPTree, List[SNMPTree]],
    parse_function: Union[SimpleSNMPParseFunction, SNMPParseFunction, None] = None,
    parsed_section_name: Optional[str] = None,
    host_label_function: Optional[HostLabelFunction] = None,
    host_label_default_parameters: Optional[ParametersTypeAlias] = None,
    host_label_ruleset_name: Optional[str] = None,
    host_label_ruleset_type: RuleSetType = RuleSetType.MERGED,
    supersedes: Optional[List[str]] = None,
) -> None:
    """Register an snmp section to checkmk

    The snmp information will be gathered and parsed according to the functions and
    options given to this function:

    Args:

      name:                The unique name of the section to be registered.

      detect:              The conditions on single OIDs that will result in the attempt to
                           fetch snmp data and discover services.
                           This should only match devices to which the section is applicable.
                           It is higly recomended to check the system description OID at the very
                           first, as this will make the discovery much more responsive and consume
                           less resources.

      fetch:               The specification of snmp data that should be fetched from the device.
                           It must be an :class:`SNMPTree` object, or a non-empty list of them.
                           The parse function will be passed a single :class:`StringTable` or a
                           list of them accordingly.

      parse_function:      The function responsible for parsing the raw snmp data.
                           It must accept exactly one argument by the name 'string_table'.
                           It will be passed either a single :class:`StringTable`, or a list
                           of them, depending on the value type of the `fetch` argument.
                           It may return an arbitrary object. Note that if the return value is
                           `None`, no forther processing will take place (just as if the agent had
                           not sent any data).
                           This function may raise arbitrary exceptions, which will be dealt with
                           by the checking engine. You should expect well formatted data.

      parsed_section_name: The name under which the parsed section will be available to the plugins.
                           Defaults to the original name.

      host_label_function: The function responsible for extracting host labels from the parsed data.
                           It must accept exactly one argument by the name 'section'.
                           When the function is called, it will be passed the parsed data as
                           returned by the parse function.
                           It is expected to yield objects of type :class:`HostLabel`.

      host_label_default_parameters: Default parameters for the host label function. Must match
                           the ValueSpec of the corresponding WATO ruleset, if it exists.

      host_label_ruleset_name: The name of the host label ruleset.

      host_label_ruleset_type: The ruleset type is either :class:`RuleSetType.ALL` or
                           :class:`RuleSetType.MERGED`.
                           It describes whether this plugins needs the merged result of the
                           effective rules, or every individual rule matching for the current host.

      supersedes:          A list of section names which are superseded by this sections. If this
                           section will be parsed to something that is not `None` (see above) all
                           superseded section will not be considered at all.

    """
    section_plugin = create_snmp_section_plugin(
        name=name,
        parsed_section_name=parsed_section_name,
        parse_function=parse_function,
        host_label_function=host_label_function,
        host_label_default_parameters=host_label_default_parameters,
        host_label_ruleset_name=host_label_ruleset_name,
        host_label_ruleset_type=host_label_ruleset_type,
        detect_spec=detect,
        fetch=fetch,
        supersedes=supersedes,
        module=get_validated_plugin_module_name(),
    )

    if is_registered_section_plugin(section_plugin.name):
        raise ValueError("duplicate section definition: %s" % section_plugin.name)

    add_section_plugin(section_plugin)


def check_plugin(
    *,
    name: str,
    sections: Optional[List[str]] = None,
    service_name: str,
    discovery_function: DiscoveryFunction,
    discovery_default_parameters: Optional[ParametersTypeAlias] = None,
    discovery_ruleset_name: Optional[str] = None,
    discovery_ruleset_type: RuleSetType = RuleSetType.MERGED,
    check_function: CheckFunction,
    check_default_parameters: Optional[ParametersTypeAlias] = None,
    check_ruleset_name: Optional[str] = None,
    cluster_check_function: Optional[Callable] = None,
) -> None:
    """Register a check plugin to checkmk.

    Args:

      name:                     The unique name of the check plugin. It must only contain the
                                characters 'A-Z', 'a-z', '0-9' and the underscore.

      sections:                 An optional list of section names that this plugin subscribes to.
                                They correspond to the 'parsed_section_name' specified in
                                :meth:`agent_section` and :meth:`snmp_section`.
                                The corresponding sections are passed to the discovery and check
                                function. The functions arguments must be called 'section_<name1>,
                                section_<name2>' ect. Defaults to a list containing as only element
                                a name equal to the name of the check plugin.

      service_name:             The template for the service name. The check function must accept
                                'item' as first argument if and only if "%s" is present in the value
                                of "service_name".

      discovery_function:       The discovery_function. Arguments must be 'params' (if discovery
                                parameters are defined) and 'section' (if the plugin subscribes
                                to a single section), or 'section_<name1>, section_<name2>' ect.
                                corresponding to the `sections`.
                                It is expected to be a generator of :class:`Service` instances.

      discovery_default_parameters: Default parameters for the discovery function. Must match the
                                ValueSpec of the corresponding WATO ruleset, if it exists.

      discovery_ruleset_name:   The name of the discovery ruleset.

      discovery_ruleset_type:   The ruleset type is either :class:`RuleSetType.ALL` or
                                :class:`RuleSetType.MERGED`.
                                It describes whether this plugins needs the merged result of the effective rules,
                                or every individual rule matching for the current host.

      check_function:           The check_function. Arguments must be 'item' (if the service has an
                                item), 'params' (if check default parameters are defined) and
                                'section' (if the plugin subscribes to a single section), or
                                'section_<name1>, section_<name2>' ect. corresponding to the
                                `sections`.

      check_default_parameters: Default parameters for the check function.
                                Must match the ValueSpec of the corresponding WATO ruleset, if it
                                exists.

      check_ruleset_name:       The name of the check ruleset.

      cluster_check_function:   The cluster check function. If this function is not specified, the
                                corresponding services will not be available for clusters.
                                The arguments are the same as the ones for the check function,
                                except that the sections are dicts (node name -> node section).

    """
    plugin = create_check_plugin(
        name=name,
        sections=sections,
        service_name=service_name,
        discovery_function=discovery_function,
        discovery_default_parameters=discovery_default_parameters,
        discovery_ruleset_name=discovery_ruleset_name,
        discovery_ruleset_type=discovery_ruleset_type,
        check_function=check_function,
        check_default_parameters=check_default_parameters,
        check_ruleset_name=check_ruleset_name,
        cluster_check_function=cluster_check_function,
        module=get_validated_plugin_module_name(),
    )

    if is_registered_check_plugin(plugin.name):
        raise ValueError("duplicate check plugin definition: %s" % plugin.name)

    add_check_plugin(plugin)
    if plugin.discovery_ruleset_name is not None:
        add_discovery_ruleset(plugin.discovery_ruleset_name)


def inventory_plugin(
    *,
    name: str,
    sections: Optional[List[str]] = None,
    inventory_function: InventoryFunction,
    inventory_default_parameters: Optional[ParametersTypeAlias] = None,
    inventory_ruleset_name: Optional[str] = None,
) -> None:
    """Register an inventory plugin to checkmk.

    Args:

      name:                     The unique name of the check plugin. It must only contain the
                                characters 'A-Z', 'a-z', '0-9' and the underscore.

      sections:                 An optional list of section names that this plugin subscribes to.
                                They correspond to the 'parsed_section_name' specified in
                                :meth:`agent_section` and :meth:`snmp_section`.
                                The corresponding sections are passed to the discovery and check
                                function. The functions arguments must be called 'section_<name1>,
                                section_<name2>' ect. Defaults to a list containing as only element
                                a name equal to the name of the inventory plugin.

      inventory_function:       The inventory_function. Arguments must be 'params' (if inventory
                                parameters are defined) and 'section' (if the plugin subscribes
                                to a single section), or 'section_<name1>, section_<name2>' ect.
                                corresponding to the `sections`.
                                It is expected to be a generator of :class:`Attributes` or
                                :class:`TableRow` instances.

      inventory_default_parameters: Default parameters for the inventory function. Must match the
                                ValueSpec of the corresponding WATO ruleset, if it exists.

      inventory_ruleset_name:   The name of the inventory ruleset.

    """
    plugin = create_inventory_plugin(
        name=name,
        sections=sections,
        inventory_function=inventory_function,
        inventory_default_parameters=inventory_default_parameters,
        inventory_ruleset_name=inventory_ruleset_name,
        module=get_validated_plugin_module_name(),
    )

    if is_registered_inventory_plugin(plugin.name):
        raise ValueError("duplicate inventory plugin definition: %s" % plugin.name)

    add_inventory_plugin(plugin)
