#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from dataclasses import dataclass
from enum import auto, Enum
from typing import Callable

from cmk.rulesets.v1._groups import (
    Functionality,
    RuleSpecCustomFunctionality,
    RuleSpecCustomTopic,
    Topic,
)
from cmk.rulesets.v1._localize import Localizable
from cmk.rulesets.v1._valuespec import Dictionary, DropdownChoice, ItemSpec, TextInput, ValueSpec


class RuleEvalType(Enum):
    MERGE = auto()
    ALL = auto()


@dataclass(frozen=True)
class RuleSpec(abc.ABC):
    def __new__(cls, *args, **kwargs):
        if cls is RuleSpec:
            raise TypeError("Cannot instantiate abstract RuleSpec.")
        return super().__new__(cls)

    name: str


@dataclass(frozen=True)
class HostRuleSpec(RuleSpec):
    title: Localizable
    topic: Topic | RuleSpecCustomTopic
    # TODO: fix functionality to specific RuleSpecFunctionality
    functionality: Functionality | RuleSpecCustomFunctionality
    value_spec: Callable[[], ValueSpec]
    eval_type: RuleEvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class ServiceRuleSpec(RuleSpec):
    title: Localizable
    topic: Topic | RuleSpecCustomTopic
    functionality: Functionality | RuleSpecCustomFunctionality
    value_spec: Callable[[], ValueSpec]
    eval_type: RuleEvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class CheckParameterRuleSpecWithItem(RuleSpec):
    title: Localizable
    topic: Topic | RuleSpecCustomTopic
    value_spec: Callable[[], Dictionary]
    item: ItemSpec
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None
    create_enforced_service = True

    @property
    def functionality(self) -> Functionality:
        return Functionality.MONITORING_CONFIGURATION

    # TODO register enforced service

    def __post_init__(self):
        assert isinstance(self.item, (TextInput, DropdownChoice))
        if not isinstance(self.topic, (Topic, RuleSpecCustomTopic)):
            raise ValueError


@dataclass(frozen=True)
class CheckParameterRuleSpecWithoutItem(RuleSpec):
    title: Localizable
    topic: Topic | RuleSpecCustomTopic
    value_spec: Callable[[], Dictionary]
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None
    create_enforced_service = True

    @property
    def functionality(self) -> Functionality:
        return Functionality.MONITORING_CONFIGURATION

    # TODO register enforced service


@dataclass(frozen=True)
class EnforcedServiceRuleSpecWithItem(RuleSpec):
    title: Localizable
    topic: Topic | RuleSpecCustomTopic
    # TODO: fix functionality to specific RuleSpecFunctionality
    functionality: Functionality | RuleSpecCustomFunctionality
    value_spec: Callable[[], ValueSpec]
    item: ItemSpec
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None

    def __post_init__(self):
        assert isinstance(self.item, (TextInput, DropdownChoice))
        if not isinstance(self.topic, (Topic, RuleSpecCustomTopic)):
            raise ValueError


@dataclass(frozen=True)
class EnforcedServiceRuleSpecWithoutItem(RuleSpec):
    title: Localizable
    topic: Topic | RuleSpecCustomTopic
    # TODO: fix functionality to specific RuleSpecFunctionality
    functionality: Functionality | RuleSpecCustomFunctionality
    value_spec: Callable[[], ValueSpec]
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class InventoryParameterRuleSpec(RuleSpec):
    title: Localizable
    topic: Topic | RuleSpecCustomTopic
    functionality: Functionality | RuleSpecCustomFunctionality
    value_spec: Callable[[], ValueSpec]
    eval_type: RuleEvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class ActiveChecksRuleSpec(RuleSpec):
    title: Localizable
    topic: Topic | RuleSpecCustomTopic
    functionality: Functionality | RuleSpecCustomFunctionality
    value_spec: Callable[[], ValueSpec]
    eval_type: RuleEvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class AgentConfigRuleSpec(RuleSpec):
    title: Localizable
    topic: Topic | RuleSpecCustomTopic
    functionality: Functionality | RuleSpecCustomFunctionality
    value_spec: Callable[[], ValueSpec]
    eval_type: RuleEvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class SpecialAgentRuleSpec(RuleSpec):
    title: Localizable
    topic: Topic | RuleSpecCustomTopic
    functionality: Functionality | RuleSpecCustomFunctionality
    value_spec: Callable[[], ValueSpec]
    eval_type: RuleEvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class ExtraHostConfRuleSpec(RuleSpec):
    title: Localizable
    topic: Topic | RuleSpecCustomTopic
    functionality: Functionality | RuleSpecCustomFunctionality
    value_spec: Callable[[], ValueSpec]
    eval_type: RuleEvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class ExtraServiceConfRuleSpec(RuleSpec):
    title: Localizable
    topic: Topic | RuleSpecCustomTopic
    functionality: Functionality | RuleSpecCustomFunctionality
    value_spec: Callable[[], ValueSpec]
    eval_type: RuleEvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None
