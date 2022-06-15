#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Type definitions

Some of these are exposed in the API, some are not.
"""
import pprint
from typing import (
    Any,
    Callable,
    Generator,
    List,
    Literal,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Union,
)

from cmk.utils.type_defs import ParsedSectionName, RuleSetName, SectionName, SNMPDetectBaseType


class PluginSuppliedLabel(
    NamedTuple(  # pylint: disable=typing-namedtuple-call
        "_LabelTuple", [("name", str), ("value", str)]
    )
):
    """A user friendly variant of our internally used labels

    This is a tiny bit redundant, but it helps decoupling API
    code from internal representations.
    """

    def __init__(self, name, value) -> None:
        super().__init__()
        if not isinstance(name, str):
            raise TypeError(f"Invalid label name given: Expected string (got {name!r})")
        if not isinstance(value, str):
            raise TypeError(f"Invalid label value given: Expected string (got {value!r})")

    def __repr__(self) -> str:
        return "%s(%r, %r)" % (self.__class__.__name__, self.name, self.value)


class HostLabel(PluginSuppliedLabel):
    """Representing a host label in Checkmk

    This class creates a host label that can be yielded by a host_label_function as regisitered
    with the section.

        >>> my_label = HostLabel("my_key", "my_value")

    """


ParametersTypeAlias = Mapping[str, Any]  # Modification may result in an incompatible API change.


class Parameters(ParametersTypeAlias):
    """Parameter objects are used to pass parameters to plugin functions"""

    def __init__(self, data) -> None:
        if not isinstance(data, dict):
            self._data = data  # error handling will try to repr(self).
            raise TypeError("Parameters expected dict, got %r" % (data,))
        self._data = dict(data)

    def __getitem__(self, key):
        return self._data[key]

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __repr__(self) -> str:
        # use pformat to be testable.
        return "%s(%s)" % (self.__class__.__name__, pprint.pformat(self._data))


class OIDSpecTuple(NamedTuple):
    column: Union[int, str]
    encoding: Literal["string", "binary"]
    save_to_cache: bool

    # we create a deepcopy in our unit tests, so support it.
    def __deepcopy__(self, _memo) -> "OIDSpecTuple":
        return self


class SNMPTreeTuple(NamedTuple):
    base: str
    oids: Sequence[OIDSpecTuple]


RuleSetTypeName = Literal["merged", "all"]

StringTable = List[List[str]]
StringByteTable = List[List[Union[str, List[int]]]]

AgentParseFunction = Callable[[StringTable], Any]

HostLabelGenerator = Generator[HostLabel, None, None]
HostLabelFunction = Callable[..., HostLabelGenerator]

SNMPParseFunction = Union[  #
    Callable[[List[StringTable]], Any],  #
    Callable[[List[StringByteTable]], Any],  #
]

SimpleSNMPParseFunction = Union[  #
    Callable[[StringTable], Any],  #
    Callable[[StringByteTable], Any],  #
]


class AgentSectionPlugin(NamedTuple):
    name: SectionName
    parsed_section_name: ParsedSectionName
    parse_function: AgentParseFunction
    host_label_function: HostLabelFunction
    host_label_default_parameters: Optional[ParametersTypeAlias]
    host_label_ruleset_name: Optional[RuleSetName]
    host_label_ruleset_type: RuleSetTypeName
    supersedes: Set[SectionName]
    module: Optional[str]  # not available for auto migrated plugins.


class SNMPSectionPlugin(NamedTuple):
    name: SectionName
    parsed_section_name: ParsedSectionName
    parse_function: SNMPParseFunction
    host_label_function: HostLabelFunction
    host_label_default_parameters: Optional[ParametersTypeAlias]
    host_label_ruleset_name: Optional[RuleSetName]
    host_label_ruleset_type: RuleSetTypeName
    detect_spec: SNMPDetectBaseType
    trees: Sequence[SNMPTreeTuple]
    supersedes: Set[SectionName]
    module: Optional[str]  # not available for auto migrated plugins.


SectionPlugin = Union[AgentSectionPlugin, SNMPSectionPlugin]
