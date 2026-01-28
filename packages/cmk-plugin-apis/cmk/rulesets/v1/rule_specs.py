#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass
from enum import auto, Enum
from keyword import iskeyword

from ._localize import Help, Title
from .form_specs import Dictionary, FormSpec, String
from .form_specs.validators import LengthInRange

# This is needed b/c sphinc will otherwise include `iskeyword` (but not the other imports)
__all__ = [
    "Topic",
    "CustomTopic",
    "EvalType",
    "HostCondition",
    "HostAndServiceCondition",
    "HostAndItemCondition",
    "Host",
    "Service",
    "CheckParameters",
    "EnforcedService",
    "DiscoveryParameters",
    "ActiveCheck",
    "AgentConfig",
    "SpecialAgent",
    "AgentAccess",
    "NotificationParameters",
    "SNMP",
    "InventoryParameters",
]


class Topic(Enum):
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
    SYNTHETIC_MONITORING = "synthetic_monitoring"
    VIRTUALIZATION = "virtualization"
    WINDOWS = "windows"


@dataclass(frozen=True)
class CustomTopic:
    """
    Args:
        title: human-readable title of this group
    """

    title: Title


class EvalType(Enum):
    MERGE = auto()
    ALL = auto()


@dataclass(frozen=True)
class HostCondition:
    """Creates a condition that allows users to match the rule based on the host."""


@dataclass(frozen=True)
class HostAndServiceCondition:
    """Creates a condition that allows users to match the rule based on the host and the service
    description."""


@dataclass(frozen=True)
class HostAndItemCondition:
    """Creates a condition that allows users to match the rule based on the host and the item of the
    service.

    Args:
        item_title: Title for the item of the service
        item_form: Configuration specification for the item of the check.
          By default, a text input field that disallows empty strings will be created.
    """

    item_title: Title
    item_form: FormSpec[str] = String(custom_validate=(LengthInRange(min_value=1),))


def _validate_name(name: str) -> None:
    # if we move away from identifiers as strings in the future, we want existing identifiers to
    # be compatible with that
    # for example in the past there already were problems with importing "if.module"
    if not name.isidentifier() or iskeyword(name):
        raise ValueError(f"'{name}' is not a valid, non-reserved Python identifier")


@dataclass(frozen=True)
class Host:
    """Specifies rule configurations for hosts

    Instances of this class will only be picked up by Checkmk if their names start with
    ``rule_spec_``.

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        eval_type: How the rules of this RuleSpec are meant to be evaluated in respect to each other
        name: Identifier of the rule spec
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Title
    topic: Topic | CustomTopic
    parameter_form: Callable[[], Dictionary]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Help | None = None

    def __post_init__(self) -> None:
        _validate_name(self.name)


@dataclass(frozen=True)
class Service:
    """Specifies rule configurations for services

    Instance of this class will only be picked up by Checkmk if their names start with
    ``rule_spec_``.

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        eval_type: How the rules of this RuleSpec are meant to be evaluated in respect to each other
        name: Identifier of the rule spec
        condition: Which targets should be configurable in the rule condition
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Title
    topic: Topic | CustomTopic
    parameter_form: Callable[[], Dictionary]
    eval_type: EvalType
    name: str
    condition: HostCondition | HostAndServiceCondition
    is_deprecated: bool = False
    help_text: Help | None = None

    def __post_init__(self) -> None:
        _validate_name(self.name)


@dataclass(frozen=True)
class CheckParameters:
    """Specifies rule configurations for checks

    Instance of this class will only be picked up by Checkmk if their names start with
    ``rule_spec_``.

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

    title: Title
    topic: Topic | CustomTopic
    parameter_form: Callable[[], Dictionary]
    name: str
    condition: HostCondition | HostAndItemCondition
    is_deprecated: bool = False
    help_text: Help | None = None
    create_enforced_service: bool = True

    def __post_init__(self) -> None:
        _validate_name(self.name)


@dataclass(frozen=True)
class EnforcedService:
    """Specifies rule configurations for checks whose creation is enforced

    Instance of this class will only be picked up by Checkmk if their names start with
    ``rule_spec_``.

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        name: Identifier of the rule spec
        condition: Which targets should be configurable in the rule condition
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Title
    topic: Topic | CustomTopic
    parameter_form: Callable[[], Dictionary] | None
    name: str
    condition: HostCondition | HostAndItemCondition
    is_deprecated: bool = False
    help_text: Help | None = None

    def __post_init__(self) -> None:
        _validate_name(self.name)


@dataclass(frozen=True)
class DiscoveryParameters:
    """Specifies configurations for the discovery of services

    Instance of this class will only be picked up by Checkmk if their names start with
    ``rule_spec_``.

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        name: Identifier of the rule spec
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Title
    topic: Topic | CustomTopic
    parameter_form: Callable[[], Dictionary]
    name: str
    is_deprecated: bool = False
    help_text: Help | None = None

    def __post_init__(self) -> None:
        _validate_name(self.name)


@dataclass(frozen=True)
class ActiveCheck:
    """Specifies rule configurations for active checks

    Instance of this class will only be picked up by Checkmk if their names start with
    ``rule_spec_``.

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        name: Identifier of the rule spec
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Title
    topic: Topic | CustomTopic
    parameter_form: Callable[[], Dictionary]
    name: str
    is_deprecated: bool = False
    help_text: Help | None = None

    def __post_init__(self) -> None:
        _validate_name(self.name)


@dataclass(frozen=True)
class AgentConfig:
    """Specifies rule configurations for agents

    Instance of this class will only be picked up by Checkmk if their names start with
    ``rule_spec_``.

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        name: Identifier of the rule spec
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Title
    topic: Topic | CustomTopic
    parameter_form: Callable[[], Dictionary]
    name: str
    is_deprecated: bool = False
    help_text: Help | None = None

    def __post_init__(self) -> None:
        _validate_name(self.name)


@dataclass(frozen=True)
class SpecialAgent:
    """Specifies rule configurations for special agents

    Instance of this class will only be picked up by Checkmk if their names start with
    ``rule_spec_``.

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        name: Identifier of the rule spec
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Title
    topic: Topic | CustomTopic
    parameter_form: Callable[[], Dictionary]
    name: str
    is_deprecated: bool = False
    help_text: Help | None = None

    def __post_init__(self) -> None:
        _validate_name(self.name)


@dataclass(frozen=True)
class AgentAccess:
    """Specifies configurations for the connection to the Checkmk and SNMP agents

    Instance of this class will only be picked up by Checkmk if their names start with
    ``rule_spec_``.

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        eval_type: How the rules of this RuleSpec are meant to be evaluated in respect to each other
        name: Identifier of the rule spec
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Title
    topic: Topic | CustomTopic
    parameter_form: Callable[[], Dictionary]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Help | None = None

    def __post_init__(self) -> None:
        _validate_name(self.name)


@dataclass(frozen=True)
class NotificationParameters:
    """Specifies rule configurations for notifications

    Instance of this class will only be picked up by Checkmk if their names start with
    ``rule_spec_``.

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        name: Identifier of the rule spec. Has to match the name of the notifications script
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Title
    topic: Topic | CustomTopic
    parameter_form: Callable[[], Dictionary]
    name: str
    is_deprecated: bool = False
    help_text: Help | None = None

    def __post_init__(self) -> None:
        _validate_name(self.name)


@dataclass(frozen=True)
class SNMP:
    """Specifies configurations for SNMP services

    Instance of this class will only be picked up by Checkmk if their names start with
    ``rule_spec_``.

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        eval_type: How the rules of this RuleSpec are meant to be evaluated in respect to each other
        name: Identifier of the rule spec
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Title
    topic: Topic | CustomTopic
    parameter_form: Callable[[], Dictionary]
    eval_type: EvalType
    name: str
    is_deprecated: bool = False
    help_text: Help | None = None

    def __post_init__(self) -> None:
        _validate_name(self.name)


@dataclass(frozen=True)
class InventoryParameters:
    """Specifies rule configurations for inventory services

    Instance of this class will only be picked up by Checkmk if their names start with
    ``rule_spec_``.

    Args:
        title: Human readable title
        topic: Categorization of the rule
        parameter_form: Configuration specification
        name: Identifier of the rule spec
        is_deprecated: Flag to indicate whether this rule is deprecated and should no longer be used
        help_text: Description to help the user with the configuration
    """

    title: Title
    topic: Topic | CustomTopic
    parameter_form: Callable[[], Dictionary]
    name: str
    is_deprecated: bool = False
    help_text: Help | None = None

    def __post_init__(self) -> None:
        _validate_name(self.name)
