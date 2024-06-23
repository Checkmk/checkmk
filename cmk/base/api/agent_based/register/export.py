#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""All objects defined here are intended to be exposed in the API
"""
from collections.abc import Callable, Mapping
from typing import Any, overload

import cmk.utils.debug

from cmk.agent_based.v1 import SNMPTree
from cmk.agent_based.v1.register import RuleSetType
from cmk.agent_based.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    HostLabelGenerator,
    InventoryResult,
    StringByteTable,
    StringTable,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    InventoryPlugin,
    SimpleSNMPSection,
    SNMPDetectSpecification,
    SNMPSection,
)

from ._discover import (
    register_agent_section,
    register_check_plugin,
    register_inventory_plugin,
    register_snmp_section,
)
from .section_plugins import create_parse_annotation, validate_parse_function
from .utils import get_validated_plugin_location

_ParametersTypeAlias = Mapping[str, Any]

# This is slightly duplcated, but I don't want to expose v2 stuff in v1, not even as part of the signature.
_HostLabelFunction = Callable[..., HostLabelGenerator]

_SNMPParseFunction = (
    Callable[[list[StringTable]], object] | Callable[[list[StringByteTable]], object]
)

_SimpleSNMPParseFunction = Callable[[StringTable], object] | Callable[[StringByteTable], object]


__all__ = [
    "agent_section",
    "snmp_section",
    "check_plugin",
    "inventory_plugin",
    "RuleSetType",
]


def _noop_agent_parse_function(string_table: StringTable) -> StringTable:
    return string_table


def _noop_snmp_parse_function(
    string_table: StringByteTable,
) -> Any:
    return string_table


def agent_section(
    *,
    name: str,
    # Note: the type is left for compatibility. It actually *is* object.
    parse_function: Callable[[StringTable], Any] | None = None,
    parsed_section_name: str | None = None,
    host_label_function: _HostLabelFunction | None = None,
    host_label_default_parameters: _ParametersTypeAlias | None = None,
    host_label_ruleset_name: str | None = None,
    host_label_ruleset_type: RuleSetType = RuleSetType.MERGED,
    supersedes: list[str] | None = None,
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
                           `None`, no further processing will take place (just as if the agent had
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
                           It describes whether this plug-in needs the merged result of the
                           effective rules, or every individual rule matching for the current host.

      supersedes:          A list of section names which are superseded by this section. If this
                           section will be parsed to something that is not `None` (see above) all
                           superseded section will not be considered at all.

    """
    if parse_function is not None:
        validate_parse_function(parse_function, expected_annotations=create_parse_annotation())

    return register_agent_section(
        # supressions: we have to live with what the old api gives us. It will be validated.
        AgentSection(  # type: ignore[misc]
            name=name,
            parse_function=_noop_agent_parse_function if parse_function is None else parse_function,
            parsed_section_name=parsed_section_name,
            host_label_function=host_label_function,
            host_label_default_parameters=host_label_default_parameters,  # type: ignore[arg-type]
            host_label_ruleset_name=host_label_ruleset_name,  # type: ignore[arg-type]
            host_label_ruleset_type=host_label_ruleset_type,
            supersedes=supersedes,
        ),
        get_validated_plugin_location(),
        validate=cmk.utils.debug.enabled(),
    )


@overload  # no List of trees -> SimpleSNMPParseFunction
def snmp_section(
    *,
    name: str,
    detect: SNMPDetectSpecification,
    fetch: SNMPTree,
    parse_function: _SimpleSNMPParseFunction | None = None,
    parsed_section_name: str | None = None,
    host_label_function: _HostLabelFunction | None = None,
    host_label_default_parameters: _ParametersTypeAlias | None = None,
    host_label_ruleset_name: str | None = None,
    host_label_ruleset_type: RuleSetType = RuleSetType.MERGED,
    supersedes: list[str] | None = None,
) -> None:
    pass


@overload
def snmp_section(
    *,
    name: str,
    detect: SNMPDetectSpecification,
    fetch: list[SNMPTree],
    parse_function: _SNMPParseFunction | None = None,
    parsed_section_name: str | None = None,
    host_label_function: _HostLabelFunction | None = None,
    host_label_default_parameters: _ParametersTypeAlias | None = None,
    host_label_ruleset_name: str | None = None,
    host_label_ruleset_type: RuleSetType = RuleSetType.MERGED,
    supersedes: list[str] | None = None,
) -> None:
    pass


def snmp_section(
    *,
    name: str,
    detect: SNMPDetectSpecification,
    fetch: SNMPTree | list[SNMPTree],
    parse_function: _SimpleSNMPParseFunction | _SNMPParseFunction | None = None,
    parsed_section_name: str | None = None,
    host_label_function: _HostLabelFunction | None = None,
    host_label_default_parameters: _ParametersTypeAlias | None = None,
    host_label_ruleset_name: str | None = None,
    host_label_ruleset_type: RuleSetType = RuleSetType.MERGED,
    supersedes: list[str] | None = None,
) -> None:
    """Register an snmp section to checkmk

    The snmp information will be gathered and parsed according to the functions and
    options given to this function:

    Args:

      name:                The unique name of the section to be registered.

      detect:              The conditions on single OIDs that will result in the attempt to
                           fetch snmp data and discover services.
                           This should only match devices to which the section is applicable.
                           It is highly recommended to check the system description OID at the very
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
                           `None`, no further processing will take place (just as if the agent had
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
                           It describes whether this plug-in needs the merged result of the
                           effective rules, or every individual rule matching for the current host.

      supersedes:          A list of section names which are superseded by this section. If this
                           section will be parsed to something that is not `None` (see above) all
                           superseded section will not be considered at all.

    """
    if parse_function is not None:
        validate_parse_function(
            parse_function,
            expected_annotations=create_parse_annotation(
                needs_bytes=any(
                    oid.encoding == "binary"
                    for tree in (fetch if isinstance(fetch, list) else [fetch])
                    for oid in tree.oids
                ),
                is_list=isinstance(fetch, list),
            ),
        )

    return register_snmp_section(
        # supressions: we have to live with what the old api gives us. It will be validated.
        (
            SNMPSection(  # type: ignore[misc]
                name=name,
                detect=detect,
                fetch=fetch,
                parse_function=_noop_snmp_parse_function if parse_function is None else parse_function,  # type: ignore[arg-type]
                parsed_section_name=parsed_section_name,
                host_label_function=host_label_function,
                host_label_default_parameters=host_label_default_parameters,  # type: ignore[arg-type]
                host_label_ruleset_name=host_label_ruleset_name,  # type: ignore[arg-type]
                host_label_ruleset_type=host_label_ruleset_type,
                supersedes=supersedes,
            )
            if isinstance(fetch, list)
            else SimpleSNMPSection(  # type: ignore[misc]
                name=name,
                detect=detect,
                fetch=fetch,
                parse_function=_noop_snmp_parse_function if parse_function is None else parse_function,  # type: ignore[arg-type]
                parsed_section_name=parsed_section_name,
                host_label_function=host_label_function,
                host_label_default_parameters=host_label_default_parameters,  # type: ignore[arg-type]
                host_label_ruleset_name=host_label_ruleset_name,  # type: ignore[arg-type]
                host_label_ruleset_type=host_label_ruleset_type,
                supersedes=supersedes,
            )
        ),
        get_validated_plugin_location(),
        validate=cmk.utils.debug.enabled(),
    )


def check_plugin(
    *,
    name: str,
    sections: list[str] | None = None,
    service_name: str,
    discovery_function: Callable[..., DiscoveryResult],
    discovery_default_parameters: _ParametersTypeAlias | None = None,
    discovery_ruleset_name: str | None = None,
    discovery_ruleset_type: RuleSetType = RuleSetType.MERGED,
    check_function: Callable[..., CheckResult],
    check_default_parameters: _ParametersTypeAlias | None = None,
    check_ruleset_name: str | None = None,
    cluster_check_function: Callable | None = None,
) -> None:
    """Register a check plug-in to checkmk.

    Args:

      name:                     The unique name of the check plug-in. It must only contain the
                                characters 'A-Z', 'a-z', '0-9' and the underscore.

      sections:                 An optional list of section names that this plug-in subscribes to.
                                They correspond to the 'parsed_section_name' specified in
                                :meth:`agent_section` and :meth:`snmp_section`.
                                The corresponding sections are passed to the discovery and check
                                function. The functions arguments must be called 'section_<name1>,
                                section_<name2>' ect. Defaults to a list containing as only element
                                a name equal to the name of the check plug-in.

      service_name:             The template for the service name. The check function must accept
                                'item' as first argument if and only if "%s" is present in the value
                                of "service_name".

      discovery_function:       The discovery_function. Arguments must be 'params' (if discovery
                                parameters are defined) and 'section' (if the plug-in subscribes
                                to a single section), or 'section_<name1>, section_<name2>' ect.
                                corresponding to the `sections`.
                                It is expected to be a generator of :class:`Service` instances.

      discovery_default_parameters: Default parameters for the discovery function. Must match the
                                ValueSpec of the corresponding WATO ruleset, if it exists.

      discovery_ruleset_name:   The name of the discovery ruleset.

      discovery_ruleset_type:   The ruleset type is either :class:`RuleSetType.ALL` or
                                :class:`RuleSetType.MERGED`.
                                It describes whether this plug-in needs the merged result of the
                                effective rules, or every individual rule matching for the current
                                host.

      check_function:           The check_function. Arguments must be 'item' (if the service has an
                                item), 'params' (if check default parameters are defined) and
                                'section' (if the plug-in subscribes to a single section), or
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
    return register_check_plugin(
        CheckPlugin(
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
        ),
        get_validated_plugin_location(),
    )


def inventory_plugin(
    *,
    name: str,
    sections: list[str] | None = None,
    inventory_function: Callable[..., InventoryResult],
    inventory_default_parameters: _ParametersTypeAlias | None = None,
    inventory_ruleset_name: str | None = None,
) -> None:
    """Register an inventory plug-in to checkmk.

    Args:

      name:                     The unique name of the check plug-in. It must only contain the
                                characters 'A-Z', 'a-z', '0-9' and the underscore.

      sections:                 An optional list of section names that this plug-in subscribes to.
                                They correspond to the 'parsed_section_name' specified in
                                :meth:`agent_section` and :meth:`snmp_section`.
                                The corresponding sections are passed to the discovery and check
                                function. The functions arguments must be called 'section_<name1>,
                                section_<name2>' ect. Defaults to a list containing as only element
                                a name equal to the name of the inventory plug-in.

      inventory_function:       The inventory_function. Arguments must be 'params' (if inventory
                                parameters are defined) and 'section' (if the plug-in subscribes
                                to a single section), or 'section_<name1>, section_<name2>' ect.
                                corresponding to the `sections`.
                                It is expected to be a generator of :class:`Attributes` or
                                :class:`TableRow` instances.

      inventory_default_parameters: Default parameters for the inventory function. Must match the
                                ValueSpec of the corresponding WATO ruleset, if it exists.

      inventory_ruleset_name:   The name of the inventory ruleset.

    """
    return register_inventory_plugin(
        InventoryPlugin(
            name=name,
            sections=sections,
            inventory_function=inventory_function,
            inventory_default_parameters=inventory_default_parameters,
            inventory_ruleset_name=inventory_ruleset_name,
        ),
        get_validated_plugin_location(),
    )
