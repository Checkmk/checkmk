#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""All objects defined here are intended to be exposed in the API"""

import functools
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Generic, Literal, overload, TypeVar

from cmk.agent_based.v1 import SNMPTree
from cmk.agent_based.v1._detection import SNMPDetectSpecification  # sorry
from cmk.agent_based.v1.register import RuleSetType
from cmk.agent_based.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    HostLabelGenerator,
    InventoryResult,
    StringByteTable,
    StringTable,
)

_Section = TypeVar("_Section", bound=object)  # yes, object.
_TableTypeT = TypeVar("_TableTypeT", StringByteTable, StringTable)
_HostLabelFunctionNoParams = Callable[[_Section], HostLabelGenerator]
_HostLabelFunctionMergedParams = Callable[[Mapping[str, object], _Section], HostLabelGenerator]
_HostLabelFunctionAllParams = Callable[
    [Sequence[Mapping[str, object]], _Section], HostLabelGenerator
]

AgentParseFunction = Callable[[StringTable], _Section | None]
InventoryFunction = Callable[..., InventoryResult]  # type: ignore[explicit-any]

CheckFunction = Callable[..., CheckResult]  # type: ignore[explicit-any]
DiscoveryFunction = Callable[..., DiscoveryResult]  # type: ignore[explicit-any]


@dataclass
class AgentSection(Generic[_Section]):
    """An AgentSection to plug into Checkmk

    Instances of this class will only be picked up by Checkmk if their names start with
    ``agent_section_``.

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

      parsed_section_name: The name under which the parsed section will be available to the
                           plug-ins.
                           Defaults to the original name.

      host_label_function: The function responsible for extracting host labels from the parsed data.
                           For unparameterized host label functions, it must accept exactly one
                           argument by the name 'section'.
                           When used in conjunction with a ruleset, it must accept two arguments:
                           'params' and 'section'.
                           The type of 'params' depends on the ruleset type. It will be a single
                           mapping for `MERGED` rulesets and a sequence of mappings for `ALL`
                           rulesets.
                           'section will be the parsed data as returned by the parse function.
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

    name: str
    parse_function: AgentParseFunction[_Section]
    parsed_section_name: str | None = None
    host_label_function: (
        _HostLabelFunctionNoParams[_Section]
        | _HostLabelFunctionMergedParams[_Section]
        | _HostLabelFunctionAllParams[_Section]
        | None
    ) = None
    host_label_default_parameters: Mapping[str, object] | None = None
    host_label_ruleset_name: str | None = None
    host_label_ruleset_type: RuleSetType = RuleSetType.MERGED
    supersedes: list[str] | None = None

    @overload
    def __init__(
        self,
        *,
        name: str,
        parse_function: AgentParseFunction[_Section],
        host_label_function: _HostLabelFunctionNoParams[_Section] | None = None,
        host_label_default_parameters: None = None,
        host_label_ruleset_name: None = None,
        host_label_ruleset_type: RuleSetType = RuleSetType.MERGED,
        parsed_section_name: str | None = None,
        supersedes: list[str] | None = None,
    ): ...

    @overload
    def __init__(
        self,
        *,
        name: str,
        parse_function: AgentParseFunction[_Section],
        host_label_function: _HostLabelFunctionMergedParams[_Section],
        host_label_default_parameters: Mapping[str, object],
        host_label_ruleset_name: str,
        host_label_ruleset_type: Literal[RuleSetType.MERGED] = RuleSetType.MERGED,
        parsed_section_name: str | None = None,
        supersedes: list[str] | None = None,
    ): ...

    @overload
    def __init__(
        self,
        *,
        name: str,
        parse_function: Callable[[StringTable], _Section | None],
        host_label_function: _HostLabelFunctionAllParams[_Section],
        host_label_default_parameters: Mapping[str, object],
        host_label_ruleset_name: str,
        host_label_ruleset_type: Literal[RuleSetType.ALL],
        parsed_section_name: str | None = None,
        supersedes: list[str] | None = None,
    ): ...

    def __init__(
        self,
        *,
        name: str,
        parse_function: Callable[[StringTable], _Section | None],
        parsed_section_name: str | None = None,
        host_label_function: (
            _HostLabelFunctionNoParams[_Section]
            | _HostLabelFunctionMergedParams[_Section]
            | _HostLabelFunctionAllParams[_Section]
            | None
        ) = None,
        host_label_default_parameters: Mapping[str, object] | None = None,
        host_label_ruleset_name: str | None = None,
        host_label_ruleset_type: RuleSetType = RuleSetType.MERGED,
        supersedes: list[str] | None = None,
    ) -> None:
        self.name = name
        self.parse_function = parse_function
        self.parsed_section_name = parsed_section_name
        self.host_label_function = host_label_function
        self.host_label_default_parameters = host_label_default_parameters
        self.host_label_ruleset_name = host_label_ruleset_name
        self.host_label_ruleset_type = host_label_ruleset_type
        self.supersedes = supersedes


@dataclass
class SimpleSNMPSection(Generic[_TableTypeT, _Section]):
    """A SimpleSNMPSection to plug into Checkmk

    Instances of this class will only be picked up by Checkmk if their names start with
    ``snmp_section_``.

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
                           It must be an :class:`SNMPTree` object.
                           The parse function will be passed a single :class:`StringTable`.

      parse_function:      The function responsible for parsing the raw snmp data.
                           It must accept exactly one argument by the name 'string_table'.
                           It will be passed a :class:`StringTable`.
                           It may return an arbitrary object. Note that if the return value is
                           `None`, no further processing will take place (just as if the agent had
                           not sent any data).
                           This function may raise arbitrary exceptions, which will be dealt with
                           by the checking engine. You should expect well formatted data.

      parsed_section_name: The name under which the parsed section will be available to the
                           plug-ins.
                           Defaults to the original name.

      host_label_function: The function responsible for extracting host labels from the parsed data.
                           For unparameterized host label functions, it must accept exactly one
                           argument by the name 'section'.
                           When used in conjunction with a ruleset, it must accept two arguments:
                           'params' and 'section'.
                           The type of 'params' depends on the ruleset type. It will be a single
                           mapping for `MERGED` rulesets and a sequence of mappings for `ALL`
                           rulesets.
                           'section will be the parsed data as returned by the parse function.
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

    name: str
    detect: SNMPDetectSpecification
    fetch: Sequence[SNMPTree]
    parse_function: Callable[[Sequence[_TableTypeT]], _Section | None]
    parsed_section_name: str | None = None
    host_label_function: (
        _HostLabelFunctionNoParams[_Section]
        | _HostLabelFunctionMergedParams[_Section]
        | _HostLabelFunctionAllParams[_Section]
        | None
    ) = None
    host_label_default_parameters: Mapping[str, object] | None = None
    host_label_ruleset_name: str | None = None
    host_label_ruleset_type: RuleSetType = RuleSetType.MERGED
    supersedes: list[str] | None = None

    @staticmethod
    def _wrap_in_upacker(
        parse_function: Callable[[_TableTypeT], _Section | None],
    ) -> Callable[[Sequence[_TableTypeT]], _Section | None]:
        @functools.wraps(parse_function)
        def unpacking_parse_function(string_table: Sequence[_TableTypeT]) -> _Section | None:
            return parse_function(string_table[0])

        return unpacking_parse_function

    @overload
    def __init__(
        self,
        *,
        name: str,
        detect: SNMPDetectSpecification,
        fetch: SNMPTree,
        parse_function: Callable[[_TableTypeT], _Section | None],
        host_label_function: _HostLabelFunctionNoParams[_Section] | None = None,
        host_label_default_parameters: None = None,
        host_label_ruleset_name: None = None,
        host_label_ruleset_type: RuleSetType = RuleSetType.MERGED,
        parsed_section_name: str | None = None,
        supersedes: list[str] | None = None,
    ): ...

    @overload
    def __init__(
        self,
        *,
        name: str,
        detect: SNMPDetectSpecification,
        fetch: SNMPTree,
        parse_function: Callable[[_TableTypeT], _Section | None],
        host_label_function: _HostLabelFunctionMergedParams[_Section],
        host_label_default_parameters: Mapping[str, object],
        host_label_ruleset_name: str,
        host_label_ruleset_type: Literal[RuleSetType.MERGED] = RuleSetType.MERGED,
        parsed_section_name: str | None = None,
        supersedes: list[str] | None = None,
    ): ...

    @overload
    def __init__(
        self,
        *,
        name: str,
        detect: SNMPDetectSpecification,
        fetch: SNMPTree,
        parse_function: Callable[[_TableTypeT], _Section | None],
        host_label_function: _HostLabelFunctionAllParams[_Section],
        host_label_default_parameters: Mapping[str, object],
        host_label_ruleset_name: str,
        host_label_ruleset_type: Literal[RuleSetType.ALL],
        parsed_section_name: str | None = None,
        supersedes: list[str] | None = None,
    ): ...

    def __init__(
        self,
        *,
        name: str,
        detect: SNMPDetectSpecification,
        fetch: SNMPTree,
        parse_function: Callable[[_TableTypeT], _Section | None],
        parsed_section_name: str | None = None,
        host_label_function: (
            _HostLabelFunctionNoParams[_Section]
            | _HostLabelFunctionMergedParams[_Section]
            | _HostLabelFunctionAllParams[_Section]
            | None
        ) = None,
        host_label_default_parameters: Mapping[str, object] | None = None,
        host_label_ruleset_name: str | None = None,
        host_label_ruleset_type: RuleSetType = RuleSetType.MERGED,
        supersedes: list[str] | None = None,
    ) -> None:
        self.name = name
        self.detect = detect
        self.fetch = [fetch]
        self.parse_function = self._wrap_in_upacker(parse_function)
        self.parsed_section_name = parsed_section_name
        self.host_label_function = host_label_function
        self.host_label_default_parameters = host_label_default_parameters
        self.host_label_ruleset_name = host_label_ruleset_name
        self.host_label_ruleset_type = host_label_ruleset_type
        self.supersedes = supersedes


@dataclass
class SNMPSection(Generic[_TableTypeT, _Section]):
    """An SNMPSection to plug into Checkmk

    Instances of this class will only be picked up by Checkmk if their names start with
    ``snmp_section_``.

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
                           It must be a non-empty list of :class:`SNMPTree` objects.
                           The parse function will be passed a non-empty list of
                           :class:`StringTable` instances accordingly.

      parse_function:      The function responsible for parsing the raw snmp data.
                           It must accept exactly one argument by the name 'string_table'.
                           It will be passed either a list of :class:`StringTable`s, matching
                           the length of the value of the `fetch` argument.
                           It may return an arbitrary object. Note that if the return value is
                           `None`, no further processing will take place (just as if the agent had
                           not sent any data).
                           This function may raise arbitrary exceptions, which will be dealt with
                           by the checking engine. You should expect well formatted data.

      parsed_section_name: The name under which the parsed section will be available to the
                           plug-ins.
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

    name: str
    detect: SNMPDetectSpecification
    fetch: Sequence[SNMPTree]
    parse_function: Callable[[Sequence[_TableTypeT]], _Section | None]
    parsed_section_name: str | None = None
    host_label_function: (
        _HostLabelFunctionNoParams[_Section]
        | _HostLabelFunctionMergedParams[_Section]
        | _HostLabelFunctionAllParams[_Section]
        | None
    ) = None
    host_label_default_parameters: Mapping[str, object] | None = None
    host_label_ruleset_name: str | None = None
    host_label_ruleset_type: RuleSetType = RuleSetType.MERGED
    supersedes: list[str] | None = None

    @overload
    def __init__(
        self,
        *,
        name: str,
        detect: SNMPDetectSpecification,
        fetch: Sequence[SNMPTree],
        parse_function: Callable[[Sequence[_TableTypeT]], _Section | None],
        host_label_function: _HostLabelFunctionNoParams[_Section] | None = None,
        host_label_default_parameters: None = None,
        host_label_ruleset_name: None = None,
        host_label_ruleset_type: RuleSetType = RuleSetType.MERGED,
        parsed_section_name: str | None = None,
        supersedes: list[str] | None = None,
    ): ...

    @overload
    def __init__(
        self,
        *,
        name: str,
        detect: SNMPDetectSpecification,
        fetch: Sequence[SNMPTree],
        parse_function: Callable[[Sequence[_TableTypeT]], _Section | None],
        host_label_function: _HostLabelFunctionAllParams[_Section],
        host_label_default_parameters: Mapping[str, object],
        host_label_ruleset_name: str,
        host_label_ruleset_type: Literal[RuleSetType.MERGED] = RuleSetType.MERGED,
        parsed_section_name: str | None = None,
        supersedes: list[str] | None = None,
    ): ...

    @overload
    def __init__(
        self,
        *,
        name: str,
        detect: SNMPDetectSpecification,
        fetch: Sequence[SNMPTree],
        parse_function: Callable[[Sequence[_TableTypeT]], _Section | None],
        host_label_function: _HostLabelFunctionAllParams[_Section],
        host_label_default_parameters: Mapping[str, object],
        host_label_ruleset_name: str,
        host_label_ruleset_type: Literal[RuleSetType.ALL],
        parsed_section_name: str | None = None,
        supersedes: list[str] | None = None,
    ): ...

    def __init__(
        self,
        *,
        name: str,
        detect: SNMPDetectSpecification,
        fetch: Sequence[SNMPTree],
        parse_function: Callable[[Sequence[_TableTypeT]], _Section | None],
        parsed_section_name: str | None = None,
        host_label_function: (
            _HostLabelFunctionNoParams[_Section]
            | _HostLabelFunctionMergedParams[_Section]
            | _HostLabelFunctionAllParams[_Section]
            | None
        ) = None,
        host_label_default_parameters: Mapping[str, object] | None = None,
        host_label_ruleset_name: str | None = None,
        host_label_ruleset_type: RuleSetType = RuleSetType.MERGED,
        supersedes: list[str] | None = None,
    ) -> None:
        self.name = name
        self.detect = detect
        self.fetch = fetch
        self.parse_function = parse_function
        self.parsed_section_name = parsed_section_name
        self.host_label_function = host_label_function
        self.host_label_default_parameters = host_label_default_parameters
        self.host_label_ruleset_name = host_label_ruleset_name
        self.host_label_ruleset_type = host_label_ruleset_type
        self.supersedes = supersedes


@dataclass(frozen=True, kw_only=True)
class CheckPlugin:
    """A CheckPlugin to plug into Checkmk.

    Instances of this class will only be picked up by Checkmk if their names start with
    ``check_plugin_``.

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

    name: str
    sections: list[str] | None = None
    service_name: str
    discovery_function: DiscoveryFunction
    discovery_default_parameters: Mapping[str, object] | None = None
    discovery_ruleset_name: str | None = None
    discovery_ruleset_type: RuleSetType = RuleSetType.MERGED
    check_function: CheckFunction
    check_default_parameters: Mapping[str, object] | None = None
    check_ruleset_name: str | None = None
    cluster_check_function: CheckFunction | None = None


@dataclass(frozen=True, kw_only=True)
class InventoryPlugin:
    """An InventoryPlugin to plug into Checkmk.

    Instances of this class will only be picked up by Checkmk if their names start with
    ``inventory_plugin_``.

    Args:

      name:                     The unique name of the plug-in. It must only contain the
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

    name: str
    sections: list[str] | None = None
    inventory_function: InventoryFunction
    inventory_default_parameters: Mapping[str, object] | None = None
    inventory_ruleset_name: str | None = None


def entry_point_prefixes() -> (  # type: ignore[explicit-any]
    Mapping[
        type[
            AgentSection[Any]
            | CheckPlugin
            | InventoryPlugin
            | SimpleSNMPSection[Any, Any]
            | SNMPSection[Any, Any]
        ],
        str,
    ]
):
    """Return the types of plug-ins and their respective prefixes that can be discovered by Checkmk.

    These types can be used to create plug-ins that can be discovered by Checkmk.
    To be discovered, the plug-in must be of one of the types returned by this function and its name
    must start with the corresponding prefix.

    Example:
    ********

    >>> for plugin_type, prefix in entry_point_prefixes().items():
    ...     print(f'{prefix}... = {plugin_type.__name__}(...)')
    snmp_section_... = SimpleSNMPSection(...)
    snmp_section_... = SNMPSection(...)
    agent_section_... = AgentSection(...)
    check_plugin_... = CheckPlugin(...)
    inventory_plugin_... = InventoryPlugin(...)
    """
    return {  # type: ignore[misc]  # expression contains Any
        SimpleSNMPSection: "snmp_section_",
        SNMPSection: "snmp_section_",
        AgentSection: "agent_section_",
        CheckPlugin: "check_plugin_",
        InventoryPlugin: "inventory_plugin_",
    }
