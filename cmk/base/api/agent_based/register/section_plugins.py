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
from cmk.utils.type_defs import ParsedSectionName, SectionName

from cmk.snmplib.type_defs import OIDBytes, OIDSpec, SNMPDetectSpec, SNMPTree

from cmk.base.api.agent_based.type_defs import (
    AgentParseFunction,
    AgentSectionPlugin,
    AgentStringTable,
    HostLabelFunction,
    SNMPParseFunction,
    SNMPSectionPlugin,
    SNMPStringByteTable,
    SNMPStringTable,
)
from cmk.base.api.agent_based.utils import parse_to_string_table
from cmk.base.api.agent_based.register.utils import validate_function_arguments

from cmk.base.discovered_labels import HostLabel


def _validate_parse_function(parse_function: Union[AgentParseFunction, SNMPParseFunction], *,
                             expected_annotation: Tuple[Type, str]) -> None:
    """Validate the parse functions signature and type"""

    if not inspect.isfunction(parse_function):
        raise TypeError("parse function must be a function: %r" % (parse_function,))

    if inspect.isgeneratorfunction(parse_function):
        raise TypeError("parse function must not be a generator function: %r" % (parse_function,))

    parameters = inspect.signature(parse_function).parameters
    if list(parameters) != ['string_table']:
        raise ValueError("parse function must accept exactly one argument 'string_table'")

    arg = parameters['string_table']
    if arg.annotation is not arg.empty:  # why is inspect._empty trueish?!
        if arg.annotation != expected_annotation[0]:
            raise TypeError('expected parse function argument annotation %r, got %r' %
                            (expected_annotation[1], arg.annotation))


def _validate_supersedings(own_name: SectionName, supersedes: List[SectionName]) -> None:
    set_supersedes = set(supersedes)
    if own_name in set_supersedes:
        raise ValueError("cannot supersede myself: '%s'" % own_name)
    if len(supersedes) != len(set_supersedes):
        raise ValueError("duplicate supersedes entry")


def _validate_detect_spec(detect_spec: SNMPDetectSpec) -> None:
    if not (isinstance(detect_spec, list) and
            all(isinstance(element, list) for element in detect_spec)):
        raise TypeError("value of 'detect' keyword must be a list of lists of 3-tuples")

    for atom in itertools.chain(*detect_spec):
        if not isinstance(atom, tuple) or not len(atom) == 3:
            raise TypeError("value of 'detect' keyword must be a list of lists of 3-tuples")
        oid_string, expression, expected_match = atom

        if not isinstance(oid_string, str):
            raise TypeError("value of 'detect' keywords first element must be a string: %r" %
                            (oid_string,))
        if not str(oid_string).startswith('.'):
            raise ValueError("OID in value of 'detect' keyword must start with '.': %r" %
                             (oid_string,))
        OIDSpec.validate(oid_string.rstrip('.*'))

        if expression is not None:
            try:
                _ = regex(expression)
            except MKGeneralException as exc:
                raise ValueError("invalid regex in value of 'detect' keyword: %s" % exc)

        if not isinstance(expected_match, bool):
            TypeError("value of 'detect' keywords third element must be a boolean: %r" %
                      (expected_match,))


def _validate_snmp_trees(trees: List[SNMPTree]) -> None:
    type_error = TypeError("value of 'trees' keyword must be a non-empty list of SNMPTrees")
    if not isinstance(trees, list):
        raise type_error
    if not trees:
        raise type_error
    if any(not isinstance(element, SNMPTree) for element in trees):
        raise type_error


def _noop_host_label_function(section: Any) -> Generator[HostLabel, None, None]:  # pylint: disable=unused-argument
    return
    yield  # pylint: disable=unreachable


def _create_host_label_function(
    host_label_function: Optional[HostLabelFunction],
    has_params: bool,
) -> HostLabelFunction:
    if host_label_function is None:
        return _noop_host_label_function

    validate_function_arguments(
        "host_label",
        host_label_function,
        has_item=False,
        sections=[ParsedSectionName("__always_just_one_section__")],
        has_params=has_params,
    )

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
    parse_function: AgentParseFunction,
    host_label_function: Optional[HostLabelFunction] = None,
    supersedes: Optional[List[str]] = None,
    module: Optional[str] = None,
) -> AgentSectionPlugin:
    """Return an AgentSectionPlugin object after validating and converting the arguments one by one

    For a detailed description of the parameters please refer to the exposed function in the
    'register' namespace of the API.
    """
    section_name = SectionName(name)

    _validate_parse_function(
        parse_function,
        expected_annotation=(AgentStringTable, "AgentStringTable"),
    )

    return AgentSectionPlugin(
        section_name,
        ParsedSectionName(parsed_section_name if parsed_section_name else str(section_name)),
        parse_function,
        _create_host_label_function(
            host_label_function,
            # TODO:
            # The following is a special case for the ps plugin. This should be done
            # in a more general sense when CMK-5158 is addressed. Make sure to grep for
            # "CMK-5158" in the code base.
            name in ("ps", "ps_lnx"),
        ),
        _create_supersedes(section_name, supersedes),
        module,
    )


def create_snmp_section_plugin(
    *,
    name: str,
    parsed_section_name: Optional[str] = None,
    parse_function: SNMPParseFunction,
    host_label_function: Optional[HostLabelFunction] = None,
    supersedes: Optional[List[str]] = None,
    detect_spec: SNMPDetectSpec,
    trees: List[SNMPTree],
    module: Optional[str] = None,
) -> SNMPSectionPlugin:
    """Return an SNMPSectionPlugin object after validating and converting the arguments one by one

    For a detailed description of the parameters please refer to the exposed function in the
    'register' namespace of the API.
    """
    section_name = SectionName(name)

    if any(isinstance(oid, OIDBytes) for tree in trees for oid in tree.oids):
        expected_annotation: Tuple[Type, str] = (SNMPStringByteTable, "SNMPStringByteTable")
    else:
        expected_annotation = (SNMPStringTable, "SNMPStringTable")

    _validate_parse_function(parse_function, expected_annotation=expected_annotation)
    _validate_detect_spec(detect_spec)
    _validate_snmp_trees(trees)

    return SNMPSectionPlugin(
        section_name,
        ParsedSectionName(parsed_section_name if parsed_section_name else str(section_name)),
        parse_function,
        _create_host_label_function(
            host_label_function,
            has_params=False,
        ),
        _create_supersedes(section_name, supersedes),
        detect_spec,
        trees,
        module,
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
            raise ValueError("Section plugin '%s' implicitly supersedes section(s) %s. "
                             "This leads to a cyclic superseding!" %
                             (name, ', '.join("'%s'" % n for n in sorted(implicitly))))
        if implicitly:
            raise ValueError("Section plugin '%s' implicitly supersedes section(s) %s. "
                             "You must add those to the supersedes keyword argument." %
                             (name, ', '.join("'%s'" % n for n in sorted(implicitly))))


def trivial_section_factory(section_name: SectionName) -> AgentSectionPlugin:
    return AgentSectionPlugin(
        name=section_name,
        parsed_section_name=ParsedSectionName(str(section_name)),
        parse_function=parse_to_string_table,
        host_label_function=_noop_host_label_function,
        supersedes=set(),
        module=None,
    )
