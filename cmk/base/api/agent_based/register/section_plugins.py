#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Background tools required to register a section plug-in"""

import functools
import inspect
import itertools
from collections.abc import Generator, Mapping, Sequence
from typing import Any

from cmk.ccc.exceptions import MKGeneralException

from cmk.utils.regex import regex
from cmk.utils.rulesets import RuleSetName
from cmk.utils.sectionname import SectionName

from cmk.snmplib import SNMPDetectBaseType

from cmk.checkengine.sectionparser import ParsedSectionName

from cmk.base.api.agent_based.plugin_classes import (
    AgentParseFunction,
    AgentSectionPlugin,
    HostLabelFunction,
    LegacyPluginLocation,
    SimpleSNMPParseFunction,
    SNMPParseFunction,
    SNMPSectionPlugin,
)
from cmk.base.api.agent_based.register.utils import (
    validate_default_parameters,
    validate_function_arguments,
    validate_ruleset_type,
)

from cmk.agent_based.v1 import HostLabel, SNMPTree
from cmk.agent_based.v1.register import RuleSetType
from cmk.agent_based.v1.type_defs import StringByteTable, StringTable
from cmk.agent_based.v2 import AgentSection, SimpleSNMPSection, SNMPSection
from cmk.discover_plugins import PluginLocation


def create_parse_annotation(
    *,
    needs_bytes: bool = False,
    is_list: bool = False,
) -> set[tuple[type, str]]:
    # this is dumb, but other approaches are not understood by mypy
    if is_list:
        if needs_bytes:
            return {
                (list[StringByteTable], "List[StringByteTable]"),
                (list[StringByteTable], "list[StringByteTable]"),
            }
        return {
            (list[StringTable], "List[StringTable]"),
            (list[StringTable], "list[StringTable]"),
        }
    if needs_bytes:
        return {(StringByteTable, "StringByteTable")}
    return {(StringTable, "StringTable")}


def validate_parse_function(
    parse_function: AgentParseFunction | SimpleSNMPParseFunction | SNMPParseFunction,
    *,
    expected_annotations: set[tuple[type, str]],
) -> None:
    """Validate the parse functions signature and type"""

    # TODO: Should we use callable() here? This is what we *actually* want to test.
    if not inspect.isfunction(parse_function):
        raise TypeError(f"parse function must be a function: {parse_function!r}")

    if inspect.isgeneratorfunction(parse_function):
        raise TypeError(f"parse function must not be a generator function: {parse_function!r}")

    parameters = inspect.signature(parse_function).parameters
    parameter_names = list(parameters)
    if parameter_names != ["string_table"]:
        raise ValueError(
            "parse function must accept exactly one argument 'string_table' (got %r)"
            % parameter_names
        )

    arg = parameters["string_table"]
    if (
        arg.annotation is not arg.empty  # arg.empty is a class, so it's trueish
        and arg.annotation not in {t for t, _ in expected_annotations}
    ):
        expected = " or ".join(repr(s) for _, s in expected_annotations)
        raise TypeError(
            f"expected parse function argument annotation {expected}, got {arg.annotation!r}"
        )


def _validate_host_label_kwargs(
    *,
    host_label_function: HostLabelFunction,
    host_label_default_parameters: Mapping[str, object] | None,
    host_label_ruleset_name: str | None,
    host_label_ruleset_type: RuleSetType,
) -> None:
    validate_ruleset_type(host_label_ruleset_type)
    validate_default_parameters(
        "host_label",
        host_label_ruleset_name,
        host_label_default_parameters,
    )

    validate_function_arguments(
        type_label="host_label",
        function=host_label_function,
        has_item=False,
        default_params=host_label_default_parameters,
        sections=[ParsedSectionName("__always_just_one_section__")],
    )


def noop_agent_parse_function(string_table: StringTable) -> StringTable:
    return string_table


def noop_snmp_parse_function(
    string_table: StringByteTable,
) -> Any:
    return string_table


def wrap_in_unpacker(parse_function: SimpleSNMPParseFunction) -> SNMPParseFunction:
    @functools.wraps(parse_function)
    def unpacking_parse_function(string_table):
        return parse_function(string_table[0])

    return unpacking_parse_function


def _validate_supersedings(own_name: SectionName, supersedes: list[SectionName]) -> None:
    set_supersedes = set(supersedes)
    if own_name in set_supersedes:
        raise ValueError(f"cannot supersede myself: '{own_name}'")
    if len(supersedes) != len(set_supersedes):
        raise ValueError("duplicate supersedes entry")


def _validate_detect_spec(detect_spec: SNMPDetectBaseType) -> None:
    if not (
        isinstance(detect_spec, list) and all(isinstance(element, list) for element in detect_spec)
    ):
        raise TypeError("value of 'detect' keyword must be a list of lists of 3-tuples")

    for atom in itertools.chain(*detect_spec):
        if not isinstance(atom, tuple) or len(atom) != 3:
            raise TypeError("value of 'detect' keyword must be a list of lists of 3-tuples")
        oid_string, expression, expected_match = atom

        if not isinstance(oid_string, str):
            raise TypeError(
                f"value of 'detect' keywords first element must be a string: {oid_string!r}"
            )
        if not str(oid_string).startswith("."):
            raise ValueError(
                f"OID in value of 'detect' keyword must start with '.': {oid_string!r}"
            )
        SNMPTree.validate_oid_string(oid_string.rstrip(".*"))

        if expression is not None:
            try:
                _ = regex(expression)
            except MKGeneralException as exc:
                raise ValueError(f"invalid regex in value of 'detect' keyword: {exc}")

        if not isinstance(expected_match, bool):
            raise TypeError(
                f"value of 'detect' keywords third element must be a boolean: {expected_match!r}"
            )


def _validate_type_list_snmp_trees(trees: Sequence[SNMPTree]) -> None:
    """Validate that we have a list of SNMPTree instances"""
    if isinstance(trees, list) and trees and all(isinstance(t, SNMPTree) for t in trees):
        return
    raise TypeError("value of 'fetch' keyword must be SNMPTree or non-empty list of SNMPTrees")


def _validate_fetch_spec(trees: Sequence[SNMPTree]) -> None:
    _validate_type_list_snmp_trees(trees)
    for tree in trees:
        tree.validate()


def _noop_host_label_function(section: Any) -> Generator[HostLabel, None, None]:
    yield from ()


def _create_host_label_function(
    host_label_function: HostLabelFunction | None,
) -> HostLabelFunction:
    if host_label_function is None:
        return _noop_host_label_function

    @functools.wraps(host_label_function)
    def filtered_generator(*args, **kwargs):
        """Only let HostLabel through

        This allows for better typing in base code.
        """
        for label in host_label_function(*args, **kwargs):
            if not isinstance(label, HostLabel):
                raise TypeError("unexpected type in host label function: %r" % type(label))
            yield label

    return filtered_generator


def _create_supersedes(
    section_name: SectionName,
    supersedes: list[str] | None,
) -> set[SectionName]:
    if supersedes is None:
        return set()

    superseded_plugins = [SectionName(n) for n in supersedes]
    _validate_supersedings(section_name, superseded_plugins)

    return set(superseded_plugins)


def create_agent_section_plugin(
    agent_section_spec: AgentSection,
    location: PluginLocation | LegacyPluginLocation,
    *,
    validate: bool,
) -> AgentSectionPlugin:
    """Return an AgentSectionPlugin object after validating and converting the arguments one by one

    For a detailed description of the parameters please refer to the exposed function in the
    'register' namespace of the API.
    """
    section_name = SectionName(agent_section_spec.name)

    if validate:
        if agent_section_spec.host_label_function is not None:
            _validate_host_label_kwargs(
                host_label_function=agent_section_spec.host_label_function,
                host_label_default_parameters=agent_section_spec.host_label_default_parameters,
                host_label_ruleset_name=agent_section_spec.host_label_ruleset_name,
                host_label_ruleset_type=agent_section_spec.host_label_ruleset_type,
            )

    return AgentSectionPlugin(
        name=section_name,
        parsed_section_name=ParsedSectionName(
            agent_section_spec.parsed_section_name or str(section_name)
        ),
        parse_function=agent_section_spec.parse_function,
        host_label_function=_create_host_label_function(agent_section_spec.host_label_function),
        host_label_default_parameters=agent_section_spec.host_label_default_parameters,
        host_label_ruleset_name=(
            None
            if agent_section_spec.host_label_ruleset_name is None
            else RuleSetName(agent_section_spec.host_label_ruleset_name)
        ),
        host_label_ruleset_type=(
            "merged" if agent_section_spec.host_label_ruleset_type is RuleSetType.MERGED else "all"
        ),
        supersedes=_create_supersedes(section_name, agent_section_spec.supersedes),
        location=location,
    )


def create_snmp_section_plugin(
    snmp_section_spec: SimpleSNMPSection | SNMPSection,
    location: PluginLocation | LegacyPluginLocation,
    *,
    validate: bool,
) -> SNMPSectionPlugin:
    """Return an SNMPSectionPlugin object after validating and converting the arguments one by one

    For a detailed description of the parameters please refer to the exposed function in the
    'register' namespace of the API.
    """
    section_name = SectionName(snmp_section_spec.name)

    if validate:
        _validate_detect_spec(snmp_section_spec.detect)
        _validate_fetch_spec(snmp_section_spec.fetch)

        if snmp_section_spec.host_label_function is not None:
            _validate_host_label_kwargs(
                host_label_function=snmp_section_spec.host_label_function,
                host_label_default_parameters=snmp_section_spec.host_label_default_parameters,
                host_label_ruleset_name=snmp_section_spec.host_label_ruleset_name,
                host_label_ruleset_type=snmp_section_spec.host_label_ruleset_type,
            )

    return SNMPSectionPlugin(
        name=section_name,
        parsed_section_name=ParsedSectionName(
            snmp_section_spec.parsed_section_name or str(section_name)
        ),
        parse_function=snmp_section_spec.parse_function,
        host_label_function=_create_host_label_function(snmp_section_spec.host_label_function),
        host_label_default_parameters=snmp_section_spec.host_label_default_parameters,
        host_label_ruleset_name=(
            None
            if snmp_section_spec.host_label_ruleset_name is None
            else RuleSetName(snmp_section_spec.host_label_ruleset_name)
        ),
        host_label_ruleset_type=(
            "merged" if snmp_section_spec.host_label_ruleset_type is RuleSetType.MERGED else "all"
        ),
        supersedes=_create_supersedes(section_name, snmp_section_spec.supersedes),
        detect_spec=snmp_section_spec.detect,
        trees=snmp_section_spec.fetch,
        location=location,
    )


def validate_section_supersedes(all_supersedes: dict[SectionName, set[SectionName]]) -> None:
    """Make sure that no sections are superseded implicitly.

    This validation makes a little extra work required for complex sepersedes,
    however it makes resolving of supersedes way more straight forward (and more explicit).
    """

    for name, explicitly in all_supersedes.items():
        transitively = {
            n for section_name in explicitly for n in all_supersedes.get(section_name, ())
        }
        implicitly = transitively - explicitly
        if name in implicitly:
            raise ValueError(
                "Section plug-in '%s' implicitly supersedes section(s) %s. "
                "This leads to a cyclic superseding!"
                % (name, ", ".join(f"'{n}'" for n in sorted(implicitly)))
            )
        if implicitly:
            raise ValueError(
                "Section plug-in '%s' implicitly supersedes section(s) %s. "
                "You must add those to the supersedes keyword argument."
                % (name, ", ".join(f"'{n}'" for n in sorted(implicitly)))
            )
