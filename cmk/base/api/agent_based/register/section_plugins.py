#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Background tools required to register a section plugin
"""
import functools
import inspect
import itertools
from typing import Any, Dict, Generator, List, Optional, Set, Tuple, Type, Union

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.regex import regex
from cmk.utils.type_defs import ParsedSectionName, RuleSetName, SectionName, SNMPDetectBaseType

from cmk.base.api.agent_based.register.utils import (
    RuleSetType,
    validate_default_parameters,
    validate_function_arguments,
    validate_ruleset_type,
)
from cmk.base.api.agent_based.section_classes import SNMPTree
from cmk.base.api.agent_based.type_defs import (
    AgentParseFunction,
    AgentSectionPlugin,
    HostLabel,
    HostLabelFunction,
    ParametersTypeAlias,
    SimpleSNMPParseFunction,
    SNMPParseFunction,
    SNMPSectionPlugin,
    StringByteTable,
    StringTable,
)


def _create_parse_annotation(
    *,
    needs_bytes: bool = False,
    is_list: bool = False,
) -> Tuple[Type, str]:
    # this is dumb, but other approaches are not understood by mypy
    if is_list:
        if needs_bytes:
            return List[StringByteTable], "List[StringByteTable]"
        return List[StringTable], "List[StringTable]"
    if needs_bytes:
        return StringByteTable, "StringByteTable"
    return StringTable, "StringTable"


def _validate_parse_function(
    parse_function: Union[AgentParseFunction, SimpleSNMPParseFunction, SNMPParseFunction],
    *,
    expected_annotation: Tuple[Type, str],
) -> None:
    """Validate the parse functions signature and type"""

    if not inspect.isfunction(parse_function):
        raise TypeError("parse function must be a function: %r" % (parse_function,))

    if inspect.isgeneratorfunction(parse_function):
        raise TypeError("parse function must not be a generator function: %r" % (parse_function,))

    parameters = inspect.signature(parse_function).parameters
    parameter_names = list(parameters)
    if parameter_names != ["string_table"]:
        raise ValueError(
            "parse function must accept exactly one argument 'string_table' (got %r)"
            % parameter_names
        )

    arg = parameters["string_table"]
    if arg.annotation is not arg.empty:  # why is inspect._empty trueish?!
        if arg.annotation != expected_annotation[0]:
            raise TypeError(
                "expected parse function argument annotation %r, got %r"
                % (expected_annotation[1], arg.annotation)
            )


def _validate_host_label_kwargs(
    *,
    host_label_function: HostLabelFunction,
    host_label_default_parameters: Optional[ParametersTypeAlias],
    host_label_ruleset_name: Optional[str],
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


def _create_agent_parse_function(
    parse_function: Optional[AgentParseFunction],
) -> AgentParseFunction:
    if parse_function is None:
        return lambda string_table: string_table

    return parse_function


def _create_snmp_parse_function(
    parse_function: Union[SimpleSNMPParseFunction, SNMPParseFunction, None],
    needs_unpacking: bool,
) -> SNMPParseFunction:
    if parse_function is None:
        if needs_unpacking:
            return lambda string_table: string_table[0]
        return lambda string_table: string_table

    if needs_unpacking:
        return lambda string_table: parse_function(string_table[0])
    # _validate_parse_function should have ensured this is the correct type:
    return parse_function  # type: ignore[return-value]


def _validate_supersedings(own_name: SectionName, supersedes: List[SectionName]) -> None:
    set_supersedes = set(supersedes)
    if own_name in set_supersedes:
        raise ValueError("cannot supersede myself: '%s'" % own_name)
    if len(supersedes) != len(set_supersedes):
        raise ValueError("duplicate supersedes entry")


def _validate_detect_spec(detect_spec: SNMPDetectBaseType) -> None:
    if not (
        isinstance(detect_spec, list) and all(isinstance(element, list) for element in detect_spec)
    ):
        raise TypeError("value of 'detect' keyword must be a list of lists of 3-tuples")

    for atom in itertools.chain(*detect_spec):
        if not isinstance(atom, tuple) or not len(atom) == 3:
            raise TypeError("value of 'detect' keyword must be a list of lists of 3-tuples")
        oid_string, expression, expected_match = atom

        if not isinstance(oid_string, str):
            raise TypeError(
                "value of 'detect' keywords first element must be a string: %r" % (oid_string,)
            )
        if not str(oid_string).startswith("."):
            raise ValueError(
                "OID in value of 'detect' keyword must start with '.': %r" % (oid_string,)
            )
        SNMPTree.validate_oid_string(oid_string.rstrip(".*"))

        if expression is not None:
            try:
                _ = regex(expression)
            except MKGeneralException as exc:
                raise ValueError("invalid regex in value of 'detect' keyword: %s" % exc)

        if not isinstance(expected_match, bool):
            TypeError(
                "value of 'detect' keywords third element must be a boolean: %r" % (expected_match,)
            )


def _validate_type_list_snmp_trees(trees: List[SNMPTree]) -> None:
    """Validate that we have a list of SNMPTree instances"""
    if isinstance(trees, list) and trees and all(isinstance(t, SNMPTree) for t in trees):
        return
    raise TypeError("value of 'fetch' keyword must be SNMPTree or non-empty list of SNMPTrees")


def _validate_fetch_spec(trees: List[SNMPTree]) -> None:
    _validate_type_list_snmp_trees(trees)
    for tree in trees:
        tree.validate()


def _noop_host_label_function(section: Any) -> Generator[HostLabel, None, None]:
    yield from ()


def _create_host_label_function(
    host_label_function: Optional[HostLabelFunction],
) -> HostLabelFunction:
    if host_label_function is None:
        return _noop_host_label_function

    @functools.wraps(host_label_function)
    def filtered_generator(*args, **kwargs):
        """Only let HostLabel through

        This allows for better typing in base code.
        """
        for label in host_label_function(  # type: ignore[misc] # Bug: None not callable
            *args,
            **kwargs,
        ):
            if not isinstance(label, HostLabel):
                raise TypeError("unexpected type in host label function: %r" % type(label))
            yield label

    return filtered_generator


def _create_supersedes(
    section_name: SectionName,
    supersedes: Optional[List[str]],
) -> Set[SectionName]:
    if supersedes is None:
        return set()

    superseded_plugins = [SectionName(n) for n in supersedes]
    _validate_supersedings(section_name, superseded_plugins)

    return set(superseded_plugins)


def create_agent_section_plugin(
    *,
    name: str,
    parsed_section_name: Optional[str] = None,
    parse_function: Optional[AgentParseFunction] = None,
    host_label_function: Optional[HostLabelFunction] = None,
    host_label_default_parameters: Optional[ParametersTypeAlias] = None,
    host_label_ruleset_name: Optional[str] = None,
    host_label_ruleset_type: RuleSetType = RuleSetType.MERGED,
    supersedes: Optional[List[str]] = None,
    module: Optional[str] = None,
    validate_creation_kwargs: bool = True,
) -> AgentSectionPlugin:
    """Return an AgentSectionPlugin object after validating and converting the arguments one by one

    For a detailed description of the parameters please refer to the exposed function in the
    'register' namespace of the API.
    """
    section_name = SectionName(name)

    if validate_creation_kwargs:
        if parse_function is not None:
            _validate_parse_function(
                parse_function,
                expected_annotation=_create_parse_annotation(),
            )

        if host_label_function is not None:
            _validate_host_label_kwargs(
                host_label_function=host_label_function,
                host_label_default_parameters=host_label_default_parameters,
                host_label_ruleset_name=host_label_ruleset_name,
                host_label_ruleset_type=host_label_ruleset_type,
            )

    return AgentSectionPlugin(
        name=section_name,
        parsed_section_name=ParsedSectionName(
            parsed_section_name if parsed_section_name else str(section_name)
        ),
        parse_function=_create_agent_parse_function(parse_function),
        host_label_function=_create_host_label_function(host_label_function),
        host_label_default_parameters=host_label_default_parameters,
        host_label_ruleset_name=(
            None if host_label_ruleset_name is None else RuleSetName(host_label_ruleset_name)
        ),
        host_label_ruleset_type=(
            "merged" if host_label_ruleset_type is RuleSetType.MERGED else "all"
        ),
        supersedes=_create_supersedes(section_name, supersedes),
        module=module,
    )


def create_snmp_section_plugin(
    *,
    name: str,
    detect_spec: SNMPDetectBaseType,
    fetch: Union[SNMPTree, List[SNMPTree]],
    parsed_section_name: Optional[str] = None,
    parse_function: Union[SimpleSNMPParseFunction, SNMPParseFunction, None] = None,
    host_label_function: Optional[HostLabelFunction] = None,
    host_label_default_parameters: Optional[ParametersTypeAlias] = None,
    host_label_ruleset_name: Optional[str] = None,
    host_label_ruleset_type: RuleSetType = RuleSetType.MERGED,
    supersedes: Optional[List[str]] = None,
    module: Optional[str] = None,
    validate_creation_kwargs: bool = True,
) -> SNMPSectionPlugin:
    """Return an SNMPSectionPlugin object after validating and converting the arguments one by one

    For a detailed description of the parameters please refer to the exposed function in the
    'register' namespace of the API.
    """
    section_name = SectionName(name)

    # normalize to List[SNMPTree]
    tree_list = [fetch] if isinstance(fetch, SNMPTree) else fetch

    if validate_creation_kwargs:
        _validate_detect_spec(detect_spec)
        _validate_fetch_spec(tree_list)

        if parse_function is not None:
            needs_bytes = any(oid.encoding == "binary" for tree in tree_list for oid in tree.oids)
            _validate_parse_function(
                parse_function,
                expected_annotation=_create_parse_annotation(
                    needs_bytes=needs_bytes,
                    is_list=isinstance(fetch, list),
                ),
            )

        if host_label_function is not None:
            _validate_host_label_kwargs(
                host_label_function=host_label_function,
                host_label_default_parameters=host_label_default_parameters,
                host_label_ruleset_name=host_label_ruleset_name,
                host_label_ruleset_type=host_label_ruleset_type,
            )

    return SNMPSectionPlugin(
        name=section_name,
        parsed_section_name=ParsedSectionName(
            parsed_section_name if parsed_section_name else str(section_name)
        ),
        parse_function=_create_snmp_parse_function(parse_function, isinstance(fetch, SNMPTree)),
        host_label_function=_create_host_label_function(host_label_function),
        host_label_default_parameters=host_label_default_parameters,
        host_label_ruleset_name=(
            None if host_label_ruleset_name is None else RuleSetName(host_label_ruleset_name)
        ),
        host_label_ruleset_type=(
            "merged" if host_label_ruleset_type is RuleSetType.MERGED else "all"
        ),
        supersedes=_create_supersedes(section_name, supersedes),
        detect_spec=detect_spec,
        trees=tree_list,
        module=module,
    )


def validate_section_supersedes(all_supersedes: Dict[SectionName, Set[SectionName]]) -> None:
    """Make sure that no sections are superseded implicitly.

    This validation makes a little extra work required for complex sepersedes,
    however it makes resolving of supersedes way more straight forward (and more explicit).
    """

    for name, explicitly in all_supersedes.items():
        transitivly = {
            n for section_name in explicitly for n in all_supersedes.get(section_name, ())
        }
        implicitly = transitivly - explicitly
        if name in implicitly:
            raise ValueError(
                "Section plugin '%s' implicitly supersedes section(s) %s. "
                "This leads to a cyclic superseding!"
                % (name, ", ".join("'%s'" % n for n in sorted(implicitly)))
            )
        if implicitly:
            raise ValueError(
                "Section plugin '%s' implicitly supersedes section(s) %s. "
                "You must add those to the supersedes keyword argument."
                % (name, ", ".join("'%s'" % n for n in sorted(implicitly)))
            )


def trivial_section_factory(section_name: SectionName) -> AgentSectionPlugin:
    return AgentSectionPlugin(
        name=section_name,
        parsed_section_name=ParsedSectionName(str(section_name)),
        parse_function=lambda string_table: string_table,
        host_label_function=_noop_host_label_function,
        host_label_default_parameters=None,
        host_label_ruleset_name=None,
        host_label_ruleset_type="merged",  # doesn't matter, use default.
        supersedes=set(),
        module=None,
    )
