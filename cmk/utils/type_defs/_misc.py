#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import dataclasses
import enum
import sys
from collections.abc import Container
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Mapping,
    NamedTuple,
    NewType,
    NoReturn,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypedDict,
    Union,
)


def assert_never(x: NoReturn) -> NoReturn:
    """A helper function that allows exhaustiveness checking with mypy:

    >>> from typing import Union
    >>> def f(x: Union[str, int]) -> None:
    ...     if isinstance(x, str):
    ...         print("str")
    ...     elif isinstance(x, int):
    ...         print("int")
    ...     else:
    ...         assert_never(foo)
    ...
    """
    raise AssertionError(f"Invalid value: {x!r}")


HostName = str
HostAddress = str
HostgroupName = str
ServiceName = str
ServicegroupName = str
ContactgroupName = str
TimeperiodName = str

AgentTargetVersion = Union[None, str, Tuple[str, str], Tuple[str, Dict[str, str]]]

AgentRawData = NewType("AgentRawData", bytes)

RulesetName = str
RuleValue = Any  # TODO: Improve this type

# FIXME: A lot of signatures regarding rules and rule sets are simply lying:
# They claim to expect a RuleConditionsSpec or Ruleset (from cmk.utils.type_defs), but
# they are silently handling a very chaotic tuple-based structure, too. We
# really, really need to fix all those signatures! Some test cases for tuples are in
# test_tuple_rulesets.py. They contain some horrible hand-made types...


# TODO: Improve this type
class RuleConditionsSpec(TypedDict, total=False):
    host_tags: Any
    host_labels: Any
    host_name: Optional[HostOrServiceConditions]
    service_description: Optional[HostOrServiceConditions]
    service_labels: Any
    host_folder: Any


# TODO: Improve this type
class _RuleSpecBase(TypedDict):
    id: str
    # TODO: Make the TypedDict generic over the value once it is supported
    # in mypy: https://github.com/python/mypy/issues/3863 (CMK-8632)
    value: Any
    condition: RuleConditionsSpec


class RuleSpec(_RuleSpecBase, total=False):
    options: RuleOptionsSpec


class RuleOptionsSpec(TypedDict, total=False):
    disabled: bool
    description: str
    comment: str
    docu_url: str
    predefined_condition_id: str


@dataclasses.dataclass()
class RuleOptions:
    disabled: Optional[bool]
    description: str
    comment: str
    docu_url: str
    predefined_condition_id: Optional[str] = None

    @classmethod
    def from_config(
        cls,
        rule_options_config: RuleOptionsSpec,
    ) -> RuleOptions:
        return cls(
            disabled=rule_options_config.get("disabled", None),
            description=rule_options_config.get("description", ""),
            comment=rule_options_config.get("comment", ""),
            docu_url=rule_options_config.get("docu_url", ""),
            predefined_condition_id=rule_options_config.get("predefined_condition_id"),
        )

    def to_config(self) -> RuleOptionsSpec:
        rule_options_config: RuleOptionsSpec = {}
        if self.disabled is not None:
            rule_options_config["disabled"] = self.disabled
        if self.description:
            rule_options_config["description"] = self.description
        if self.comment:
            rule_options_config["comment"] = self.comment
        if self.docu_url:
            rule_options_config["docu_url"] = self.docu_url
        if self.predefined_condition_id:
            rule_options_config["predefined_condition_id"] = self.predefined_condition_id
        return rule_options_config


HostOrServiceConditionRegex = TypedDict(
    "HostOrServiceConditionRegex",
    {"$regex": str},
)
HostOrServiceConditionsSimple = List[Union[HostOrServiceConditionRegex, str]]
HostOrServiceConditionsNegated = TypedDict(
    "HostOrServiceConditionsNegated",
    {"$nor": HostOrServiceConditionsSimple},
)

HostOrServiceConditions = Union[
    HostOrServiceConditionsSimple,
    HostOrServiceConditionsNegated,
]  # TODO: refine type

Ruleset = List[RuleSpec]  # TODO: Improve this type
CheckPluginNameStr = str
ActiveCheckPluginName = str
Item = Optional[str]
Labels = Mapping[str, str]
LabelSources = Dict[str, str]

TagID = str
TaggroupID = str
TaggroupIDToTagID = Mapping[TaggroupID, TagID]
TagIDToTaggroupID = Mapping[TagID, TaggroupID]
TagIDs = Set[TagID]
TagConditionNE = TypedDict(
    "TagConditionNE",
    {
        "$ne": Optional[TagID],
    },
)
TagConditionOR = TypedDict(
    "TagConditionOR",
    {
        "$or": Sequence[Optional[TagID]],
    },
)
TagConditionNOR = TypedDict(
    "TagConditionNOR",
    {
        "$nor": Sequence[Optional[TagID]],
    },
)
TagCondition = Union[Optional[TagID], TagConditionNE, TagConditionOR, TagConditionNOR]
# Here, we have data structures such as
# {'ip-v4': {'$ne': 'ip-v4'}, 'snmp_ds': {'$nor': ['no-snmp', 'snmp-v1']}, 'taggroup_02': None, 'aux_tag_01': 'aux_tag_01', 'address_family': 'ip-v4-only'}
TaggroupIDToTagCondition = Mapping[TaggroupID, TagCondition]
TagsOfHosts = Dict[HostName, TaggroupIDToTagID]

LabelConditions = Dict[str, Union[str, TagConditionNE]]


class GroupedTagSpec(TypedDict):
    id: Optional[TagID]
    title: str
    aux_tags: List[TagID]


class _AuxTagSpecOpt(TypedDict, total=False):
    topic: str


class AuxTagSpec(_AuxTagSpecOpt):
    id: TagID
    title: str


class _TaggroupSpecOpt(TypedDict, total=False):
    topic: str
    help: str


class TaggroupSpec(_TaggroupSpecOpt):
    id: TaggroupID
    title: str
    tags: List[GroupedTagSpec]


class TagConfigSpec(TypedDict):
    tag_groups: List[TaggroupSpec]
    aux_tags: List[AuxTagSpec]


CheckVariables = Dict[str, Any]
Seconds = int
Timestamp = int
TimeRange = Tuple[int, int]

ServiceState = int
HostState = int
ServiceDetails = str
ServiceAdditionalDetails = str

MetricName = str
MetricTuple = Tuple[
    MetricName,
    float,
    Optional[float],
    Optional[float],
    Optional[float],
    Optional[float],
]

ClusterMode = Literal["native", "failover", "worst", "best"]

LegacyCheckParameters = Union[None, Mapping, Tuple, List, str, int, bool]

SetAutochecksTable = Dict[
    Tuple[str, Item], Tuple[ServiceName, LegacyCheckParameters, Labels, List[HostName]]
]

SetAutochecksTablePre20 = Dict[Tuple[str, Item], Tuple[Dict[str, Any], Labels]]


@dataclass
class DiscoveryResult:
    self_new: int = 0
    self_removed: int = 0
    self_kept: int = 0
    self_total: int = 0
    self_new_host_labels: int = 0
    self_total_host_labels: int = 0
    clustered_new: int = 0
    clustered_old: int = 0
    clustered_vanished: int = 0
    clustered_ignored: int = 0

    # None  -> No error occured
    # ""    -> Not monitored (disabled host)
    # "..." -> An error message about the failed discovery
    error_text: Optional[str] = None

    # An optional text to describe the services changed by the operation
    diff_text: Optional[str] = None


UserId = NewType("UserId", str)

# This def is used to keep the API-exposed object in sync with our
# implementation.
SNMPDetectBaseType = List[List[Tuple[str, str, bool]]]

# TODO: TimeperiodSpec should really be a class or at least a NamedTuple! We
# can easily transform back and forth for serialization.
TimeperiodSpec = Dict[str, Union[str, List[str], List[Tuple[str, str]]]]
TimeperiodSpecs = Dict[TimeperiodName, TimeperiodSpec]


class SourceType(enum.Enum):
    """Classification of management sources vs regular hosts"""

    HOST = "HOST"
    MANAGEMENT = "MANAGEMENT"


class HostKey(NamedTuple):
    hostname: HostName
    ipaddress: Optional[HostAddress]
    source_type: SourceType


# TODO: We should really parse our configuration file and use a
# class/NamedTuple, see above.
def timeperiod_spec_alias(timeperiod_spec: TimeperiodSpec, default: str = "") -> str:
    alias = timeperiod_spec.get("alias", default)
    if isinstance(alias, str):
        return alias
    raise Exception("invalid timeperiod alias %r" % (alias,))


class EvalableFloat(float):
    """Extends the float representation for Infinities in such way that
    they can be parsed by eval"""

    def __str__(self):
        return super().__repr__()

    def __repr__(self) -> str:
        if self > sys.float_info.max:
            return "1e%d" % (sys.float_info.max_10_exp + 1)
        if self < -1 * sys.float_info.max:
            return "-1e%d" % (sys.float_info.max_10_exp + 1)
        return super().__repr__()


class _Everything(Container):
    def __contains__(self, other: object) -> bool:
        return True


EVERYTHING = _Everything()

# Symbolic representations of states in plugin output
# TODO(ml): Should probably be of type enum::int -> str
state_markers = ("", "(!)", "(!!)", "(?)")


class ExitSpec(TypedDict, total=False):
    empty_output: int
    connection: int
    timeout: int
    exception: int
    wrong_version: int
    missing_sections: int
    specific_missing_sections: List[Tuple[str, int]]
    restricted_address_mismatch: int
    legacy_pull_mode: int


class HostLabelValueDict(TypedDict):
    value: str
    plugin_name: Optional[str]


DiscoveredHostLabelsDict = Dict[str, HostLabelValueDict]
