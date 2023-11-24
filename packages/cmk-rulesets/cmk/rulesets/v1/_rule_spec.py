#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from enum import auto, Enum
from typing import Callable

from cmk.rulesets.v1._form_spec import Dictionary, DropdownChoice, FormSpec, ItemFormSpec, TextInput
from cmk.rulesets.v1._groups import CustomFunctionality, CustomTopic, Functionality, Topic
from cmk.rulesets.v1._localize import Localizable


class RuleEvalType(Enum):
    MERGE = auto()
    ALL = auto()


@dataclass(frozen=True)
class HostRuleSpec:
    title: Localizable
    topic: Topic | CustomTopic
    # TODO: fix functionality to specific RuleSpecFunctionality
    functionality: Functionality | CustomFunctionality
    parameter_form: Callable[[], FormSpec]
    eval_type: RuleEvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class ServiceRuleSpec:
    title: Localizable
    topic: Topic | CustomTopic
    functionality: Functionality | CustomFunctionality
    parameter_form: Callable[[], FormSpec]
    eval_type: RuleEvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class CheckParameterRuleSpecWithItem:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], Dictionary]
    item_form: ItemFormSpec
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None
    create_enforced_service = True

    @property
    def functionality(self) -> Functionality:
        return Functionality.MONITORING_CONFIGURATION

    def __post_init__(self) -> None:
        assert isinstance(self.item_form, (TextInput, DropdownChoice))
        if not isinstance(self.topic, (Topic, CustomTopic)):
            raise ValueError


@dataclass(frozen=True)
class CheckParameterRuleSpecWithoutItem:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], Dictionary]
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None
    create_enforced_service = True

    @property
    def functionality(self) -> Functionality:
        return Functionality.MONITORING_CONFIGURATION


@dataclass(frozen=True)
class EnforcedServiceRuleSpecWithItem:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec] | None
    item_form: ItemFormSpec
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None

    @property
    def functionality(self) -> Functionality:
        return Functionality.ENFORCED_SERVICES

    def __post_init__(self) -> None:
        assert isinstance(self.item_form, (TextInput, DropdownChoice))
        if not isinstance(self.topic, (Topic, CustomTopic)):
            raise ValueError


@dataclass(frozen=True)
class EnforcedServiceRuleSpecWithoutItem:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec] | None
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None

    @property
    def functionality(self) -> Functionality:
        return Functionality.ENFORCED_SERVICES

    def __post_init__(self) -> None:
        if not isinstance(self.topic, (Topic, CustomTopic)):
            raise ValueError


@dataclass(frozen=True)
class InventoryParameterRuleSpec:
    title: Localizable
    topic: Topic | CustomTopic
    functionality: Functionality | CustomFunctionality
    parameter_form: Callable[[], FormSpec]
    eval_type: RuleEvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class ActiveChecksRuleSpec:
    title: Localizable
    topic: Topic | CustomTopic
    functionality: Functionality | CustomFunctionality
    parameter_form: Callable[[], FormSpec]
    eval_type: RuleEvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class AgentConfigRuleSpec:
    title: Localizable
    topic: Topic | CustomTopic
    functionality: Functionality | CustomFunctionality
    parameter_form: Callable[[], FormSpec]
    eval_type: RuleEvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class SpecialAgentRuleSpec:
    title: Localizable
    topic: Topic | CustomTopic
    functionality: Functionality | CustomFunctionality
    parameter_form: Callable[[], FormSpec]
    eval_type: RuleEvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class ExtraHostConfRuleSpec:
    title: Localizable
    topic: Topic | CustomTopic
    functionality: Functionality | CustomFunctionality
    parameter_form: Callable[[], FormSpec]
    eval_type: RuleEvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class ExtraServiceConfRuleSpec:
    title: Localizable
    topic: Topic | CustomTopic
    functionality: Functionality | CustomFunctionality
    parameter_form: Callable[[], FormSpec]
    eval_type: RuleEvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None
