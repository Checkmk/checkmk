#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from enum import auto, Enum
from typing import Callable

from ._localize import Localizable
from .form_specs import Dictionary, DropdownChoice, FormSpec, ItemFormSpec, TextInput


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
class HostMonitoring:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class ServiceMonitoringWithoutService:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class ServiceMonitoring:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class CheckParameterWithItem:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], Dictionary]
    item_form: ItemFormSpec
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None
    create_enforced_service: bool = True

    def __post_init__(self) -> None:
        assert isinstance(self.item_form, (TextInput, DropdownChoice))
        if not isinstance(self.topic, (Topic, CustomTopic)):
            raise ValueError


@dataclass(frozen=True)
class CheckParameterWithoutItem:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], Dictionary]
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None
    create_enforced_service: bool = True


@dataclass(frozen=True)
class EnforcedServiceWithItem:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec] | None
    item_form: ItemFormSpec
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None

    def __post_init__(self) -> None:
        assert isinstance(self.item_form, (TextInput, DropdownChoice))
        if not isinstance(self.topic, (Topic, CustomTopic)):
            raise ValueError


@dataclass(frozen=True)
class EnforcedServiceWithoutItem:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec] | None
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.topic, (Topic, CustomTopic)):
            raise ValueError


@dataclass(frozen=True)
class DiscoveryParameters:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class ActiveChecks:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class AgentConfig:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class SpecialAgent:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class AgentAccess:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class NotificationParameters:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class SNMP:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class InventoryParameters:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class ExtraHostConfEventConsole:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class ExtraHostConfHostMonitoring:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None


@dataclass(frozen=True)
class ExtraServiceConf:
    title: Localizable
    topic: Topic | CustomTopic
    parameter_form: Callable[[], FormSpec]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Localizable | None = None
