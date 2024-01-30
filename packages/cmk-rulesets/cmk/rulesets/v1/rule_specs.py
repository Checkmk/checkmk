#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass
from enum import auto, Enum

from ._localize import Localizable
from .form_specs import Dictionary, FormSpec, ItemFormSpec, SingleChoice, Text


class Topic(Enum):
    AGENT_PLUGINS = "agent_plugins"
    APPLICATIONS = "applications"
    CACHING_MESSAGE_QUEUES = "cache_message_queues"
    CLOUD = "cloud"
    CONFIGURATION_DEPLOYMENT = "configuration_deployment"
    DATABASES = "databases"
    GENERAL = "general"
    ENVIRONMENTAL = "environmental"
    LINUX = "linux"
    NETWORKING = "networking"
    MIDDLEWARE = "middleware"
    NOTIFICATIONS = "notifications"
    OPERATING_SYSTEM = "operating_system"
    PERIPHERALS = "peripherals"
    POWER = "power"
    SERVER_HARDWARE = "server_hardware"
    STORAGE = "storage"
    VIRTUALIZATION = "virtualization"
    WINDOWS = "windows"


@dataclass(frozen=True)
class CustomTopic:
    """
    Args:
        title: human-readable title of this group
    """

    title: Localizable


class EvalType(Enum):
    MERGE = auto()
    ALL = auto()


@dataclass(frozen=True)
class HostCondition:
    ...


@dataclass(frozen=True)
class HostAndServiceCondition:
    ...


@dataclass(frozen=True)
class HostAndItemCondition:
    """
    Args:
        item_form: Configuration specification for the item of the check
    """

    item_form: ItemFormSpec


@dataclass(frozen=True)
class Host:
    """Specifies rule configurations for hosts

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        eval_type: How the rules of this RuleSpec are evaluated in respect to each other
        name: Identifier of the rule spec
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class Service:
    """Specifies rule configurations for services

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        eval_type: How the rules of this RuleSpec are evaluated in respect to each other
        name: Identifier of the rule spec
        condition: Which targets should be configurable in the rule condition
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    condition: HostCondition | HostAndServiceCondition
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class CheckParameters:
    """Specifies rule configurations for checks

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        name: Identifier of the rule spec
        condition: Which targets should be configurable in the rule condition
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
        create_enforced_service: Whether to automatically create an enforced service for any
                                  service created with this rule spec
    """

    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], Dictionary]
    name: str
    condition: HostCondition | HostAndItemCondition
    is_deprecated: bool = False
    help_text: Localizable | None = None
    create_enforced_service: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.condition, HostAndItemCondition):
            assert isinstance(self.condition.item_form, (Text, SingleChoice))
        if not isinstance(self.topic, (Topic, CustomTopic)):
            raise ValueError


@dataclass(frozen=True)
class EnforcedService:
    """Specifies rule configurations for checks whose creation is enforced

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        name: Identifier of the rule spec
        condition: Which targets should be configurable in the rule condition
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec] | None
    name: str
    condition: HostCondition | HostAndItemCondition
    is_deprecated: bool = False
    help_text: Localizable | None = None

    def __post_init__(self) -> None:
        if isinstance(self.condition, HostAndItemCondition):
            assert isinstance(self.condition.item_form, (Text, SingleChoice))
        if not isinstance(self.topic, (Topic, CustomTopic)):
            raise ValueError


@dataclass(frozen=True)
class DiscoveryParameters:
    """Specifies configurations for the discovery of services

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        eval_type: How the rules of this RuleSpec are evaluated in respect to each other
        name: Identifier of the rule spec
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class ActiveCheck:
    """Specifies rule configurations for active checks

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        eval_type: How the rules of this RuleSpec are evaluated in respect to each other
        name: Identifier of the rule spec
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class AgentConfig:
    """Specifies rule configurations for agents

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        eval_type: How the rules of this RuleSpec are evaluated in respect to each other
        name: Identifier of the rule spec
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class SpecialAgent:
    """Specifies rule configurations for special agents

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        eval_type: How the rules of this RuleSpec are evaluated in respect to each other
        name: Identifier of the rule spec
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class AgentAccess:
    """Specifies configurations for the connection to the Checkmk and SNMP agents

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        eval_type: How the rules of this RuleSpec are evaluated in respect to each other
        name: Identifier of the rule spec
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class NotificationParameters:
    """Specifies rule configurations for notifications

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        eval_type: How the rules of this RuleSpec are evaluated in respect to each other
        name: Identifier of the rule spec
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class SNMP:
    """Specifies configurations for SNMP services

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        eval_type: How the rules of this RuleSpec are evaluated in respect to each other
        name: Identifier of the rule spec
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class InventoryParameters:
    """Specifies rule configurations for inventory services

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        eval_type: How the rules of this RuleSpec are evaluated in respect to each other
        name: Identifier of the rule spec
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None
