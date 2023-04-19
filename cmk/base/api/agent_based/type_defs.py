#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Type definitions

Some of these are exposed in the API, some are not.
"""

import pprint
from collections.abc import Iterator
from typing import (
    Any,
    Callable,
    Generator,
    List,
    Literal,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Union,
)

from cmk.utils.type_defs import (
    ParametersTypeAlias,
    ParsedSectionName,
    RuleSetName,
    SectionName,
    SNMPDetectBaseType,
)

from cmk.checkers import HostLabel


class Parameters(ParametersTypeAlias):
    """Parameter objects are used to pass parameters to plugin functions"""

    def __init__(self, data: ParametersTypeAlias) -> None:
        self._data = dict(data)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __repr__(self) -> str:
        # use pformat to be testable.
        return "%s(%s)" % (self.__class__.__name__, pprint.pformat(self._data))


class OIDSpecTuple(NamedTuple):
    column: Union[int, str]
    encoding: Literal["string", "binary"]
    save_to_cache: bool

    # we create a deepcopy in our unit tests, so support it.
    def __deepcopy__(self, _memo: object) -> "OIDSpecTuple":
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
