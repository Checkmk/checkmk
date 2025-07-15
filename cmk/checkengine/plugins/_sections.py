#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, Literal, NamedTuple, Protocol

from cmk.agent_based.v2 import (
    HostLabelGenerator,
    StringByteTable,
    StringTable,
)
from cmk.checkengine.sectionparser import ParsedSectionName
from cmk.discover_plugins import PluginLocation
from cmk.snmplib import SNMPDetectBaseType
from cmk.utils.rulesets import RuleSetName
from cmk.utils.sectionname import SectionName

from ._common import LegacyPluginLocation, RuleSetTypeName

AgentParseFunction = Callable[[StringTable], Any]

HostLabelFunction = Callable[..., HostLabelGenerator]

SNMPParseFunction = Callable[[list[StringTable]], Any] | Callable[[list[StringByteTable]], Any]

SimpleSNMPParseFunction = Callable[[StringTable], Any] | Callable[[StringByteTable], Any]


class AgentSectionPlugin(NamedTuple):
    name: SectionName
    parsed_section_name: ParsedSectionName
    parse_function: AgentParseFunction
    host_label_function: HostLabelFunction
    host_label_default_parameters: Mapping[str, object] | None
    host_label_ruleset_name: RuleSetName | None
    host_label_ruleset_type: RuleSetTypeName
    supersedes: set[SectionName]
    # We need to allow 'None' for the trivial agent section :-|
    location: PluginLocation | LegacyPluginLocation | None


class _OIDSpecLike(Protocol):
    @property
    def column(self) -> int | str: ...

    @property
    def encoding(self) -> Literal["string", "binary"]: ...

    @property
    def save_to_cache(self) -> bool: ...


class _SNMPTreeLike(Protocol):
    @property
    def base(self) -> str: ...

    @property
    def oids(self) -> Sequence[_OIDSpecLike]: ...


class SNMPSectionPlugin(NamedTuple):
    name: SectionName
    parsed_section_name: ParsedSectionName
    parse_function: SNMPParseFunction
    host_label_function: HostLabelFunction
    host_label_default_parameters: Mapping[str, object] | None
    host_label_ruleset_name: RuleSetName | None
    host_label_ruleset_type: RuleSetTypeName
    detect_spec: SNMPDetectBaseType
    trees: Sequence[_SNMPTreeLike]
    supersedes: set[SectionName]
    location: PluginLocation | LegacyPluginLocation


SectionPlugin = AgentSectionPlugin | SNMPSectionPlugin
