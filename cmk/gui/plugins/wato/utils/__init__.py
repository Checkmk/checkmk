#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for Setup internals and the Setup plugins"""

# ruff: noqa: F401

# TODO: More feature related splitting up would be better

import abc
import json
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any, cast, Literal

from livestatus import SiteConfiguration, SiteConfigurations

import cmk.ccc.plugin_registry
import cmk.ccc.version as cmk_version
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition, edition

from cmk.utils.rulesets.definition import RuleGroup

from cmk.checkengine.plugins import CheckPluginName

import cmk.gui.watolib.rulespecs as _rulespecs
from cmk.gui import forms, hooks, userdb, weblib
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _u
from cmk.gui.logged_in import user
from cmk.gui.pages import page_registry
from cmk.gui.permissions import permission_section_registry, PermissionSection
from cmk.gui.site_config import is_wato_slave_site as is_wato_slave_site
from cmk.gui.type_defs import Choices as Choices
from cmk.gui.type_defs import ChoiceText as ChoiceText
from cmk.gui.utils.html import HTML as HTML
from cmk.gui.utils.transaction_manager import transactions as transactions
from cmk.gui.utils.urls import make_confirm_link as make_confirm_link
from cmk.gui.valuespec import Alternative as Alternative
from cmk.gui.valuespec import CascadingDropdown as CascadingDropdown
from cmk.gui.valuespec import Dictionary as Dictionary
from cmk.gui.valuespec import DictionaryEntry as DictionaryEntry
from cmk.gui.valuespec import DropdownChoice as DropdownChoice
from cmk.gui.valuespec import DropdownChoiceEntries as DropdownChoiceEntries
from cmk.gui.valuespec import DualListChoice as DualListChoice
from cmk.gui.valuespec import FixedValue as FixedValue
from cmk.gui.valuespec import Float as Float
from cmk.gui.valuespec import Integer as Integer
from cmk.gui.valuespec import JSONValue as JSONValue
from cmk.gui.valuespec import Labels as Labels
from cmk.gui.valuespec import ListChoice as ListChoice
from cmk.gui.valuespec import ListOf as ListOf
from cmk.gui.valuespec import ListOfMultiple as ListOfMultiple
from cmk.gui.valuespec import ListOfStrings as ListOfStrings
from cmk.gui.valuespec import MonitoredHostname as MonitoredHostname
from cmk.gui.valuespec import Password as Password
from cmk.gui.valuespec import Percentage as Percentage
from cmk.gui.valuespec import RegExp as RegExp
from cmk.gui.valuespec import TextInput as TextInput
from cmk.gui.valuespec import Tuple as Tuple
from cmk.gui.valuespec import Url as Url
from cmk.gui.valuespec import ValueSpec as ValueSpec
from cmk.gui.valuespec import ValueSpecHelp as ValueSpecHelp
from cmk.gui.valuespec import ValueSpecText as ValueSpecText
from cmk.gui.wato import Levels as Levels
from cmk.gui.wato import PredictiveLevels as PredictiveLevels
from cmk.gui.wato import (
    RulespecGroupCheckParametersApplications as RulespecGroupCheckParametersApplications,
)
from cmk.gui.wato import (
    RulespecGroupCheckParametersDiscovery as RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.wato import (
    RulespecGroupCheckParametersEnvironment as RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.wato import (
    RulespecGroupCheckParametersHardware as RulespecGroupCheckParametersHardware,
)
from cmk.gui.wato import (
    RulespecGroupCheckParametersNetworking as RulespecGroupCheckParametersNetworking,
)
from cmk.gui.wato import (
    RulespecGroupCheckParametersOperatingSystem as RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.wato import (
    RulespecGroupCheckParametersPrinters as RulespecGroupCheckParametersPrinters,
)
from cmk.gui.wato import RulespecGroupCheckParametersStorage as RulespecGroupCheckParametersStorage
from cmk.gui.wato import (
    RulespecGroupCheckParametersVirtualization as RulespecGroupCheckParametersVirtualization,
)
from cmk.gui.wato import (
    RulespecGroupDiscoveryCheckParameters as RulespecGroupDiscoveryCheckParameters,
)
from cmk.gui.watolib.attributes import IPMIParameters as IPMIParameters
from cmk.gui.watolib.attributes import SNMPCredentials as SNMPCredentials
from cmk.gui.watolib.config_domains import ConfigDomainCore as _ConfigDomainCore
from cmk.gui.watolib.config_hostname import ConfigHostname as ConfigHostname
from cmk.gui.watolib.config_sync import ReplicationPath as ReplicationPath
from cmk.gui.watolib.config_variable_groups import (
    ConfigVariableGroupNotifications as ConfigVariableGroupNotifications,
)
from cmk.gui.watolib.config_variable_groups import (
    ConfigVariableGroupSiteManagement as ConfigVariableGroupSiteManagement,
)
from cmk.gui.watolib.config_variable_groups import (
    ConfigVariableGroupUserInterface as ConfigVariableGroupUserInterface,
)
from cmk.gui.watolib.config_variable_groups import (
    ConfigVariableGroupWATO as ConfigVariableGroupWATO,
)
from cmk.gui.watolib.host_attributes import ABCHostAttributeNagiosText as ABCHostAttributeNagiosText
from cmk.gui.watolib.host_attributes import (
    ABCHostAttributeNagiosValueSpec as ABCHostAttributeNagiosValueSpec,
)
from cmk.gui.watolib.host_attributes import ABCHostAttributeValueSpec as ABCHostAttributeValueSpec
from cmk.gui.watolib.host_attributes import (
    HOST_ATTRIBUTE_TOPIC_BASIC_SETTINGS as HOST_ATTRIBUTE_TOPIC_BASIC_SETTINGS,
)
from cmk.gui.watolib.host_attributes import (
    HOST_ATTRIBUTE_TOPIC_CUSTOM_ATTRIBUTES as HOST_ATTRIBUTE_TOPIC_CUSTOM_ATTRIBUTES,
)
from cmk.gui.watolib.host_attributes import (
    HOST_ATTRIBUTE_TOPIC_HOST_TAGS as HOST_ATTRIBUTE_TOPIC_HOST_TAGS,
)
from cmk.gui.watolib.host_attributes import (
    HOST_ATTRIBUTE_TOPIC_MANAGEMENT_BOARD as HOST_ATTRIBUTE_TOPIC_MANAGEMENT_BOARD,
)
from cmk.gui.watolib.host_attributes import (
    HOST_ATTRIBUTE_TOPIC_META_DATA as HOST_ATTRIBUTE_TOPIC_META_DATA,
)
from cmk.gui.watolib.host_attributes import (
    HOST_ATTRIBUTE_TOPIC_MONITORING_DATASOURCES as HOST_ATTRIBUTE_TOPIC_MONITORING_DATASOURCES,
)
from cmk.gui.watolib.host_attributes import (
    HOST_ATTRIBUTE_TOPIC_NETWORK_ADDRESS as HOST_ATTRIBUTE_TOPIC_NETWORK_ADDRESS,
)
from cmk.gui.watolib.host_attributes import (
    HOST_ATTRIBUTE_TOPIC_NETWORK_SCAN as HOST_ATTRIBUTE_TOPIC_NETWORK_SCAN,
)
from cmk.gui.watolib.host_attributes import (
    host_attribute_topic_registry as host_attribute_topic_registry,
)
from cmk.gui.watolib.hosts_and_folders import Folder as Folder
from cmk.gui.watolib.hosts_and_folders import folder_from_request as folder_from_request
from cmk.gui.watolib.hosts_and_folders import folder_tree as folder_tree
from cmk.gui.watolib.hosts_and_folders import Host as Host
from cmk.gui.watolib.hosts_and_folders import SearchFolder as SearchFolder
from cmk.gui.watolib.main_menu import ABCMainModule as ABCMainModule
from cmk.gui.watolib.main_menu import main_module_registry as main_module_registry
from cmk.gui.watolib.main_menu import MainModuleTopic as MainModuleTopic
from cmk.gui.watolib.main_menu import MenuItem as MenuItem
from cmk.gui.watolib.password_store import PasswordStore as PasswordStore
from cmk.gui.watolib.rulespec_groups import RulespecGroupAgentSNMP as RulespecGroupAgentSNMP
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupEnforcedServicesApplications as RulespecGroupEnforcedServicesApplications,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupEnforcedServicesEnvironment as RulespecGroupEnforcedServicesEnvironment,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupEnforcedServicesHardware as RulespecGroupEnforcedServicesHardware,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupEnforcedServicesNetworking as RulespecGroupEnforcedServicesNetworking,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupEnforcedServicesOperatingSystem as RulespecGroupEnforcedServicesOperatingSystem,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupEnforcedServicesStorage as RulespecGroupEnforcedServicesStorage,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupEnforcedServicesVirtualization as RulespecGroupEnforcedServicesVirtualization,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupHostsMonitoringRulesHostChecks as RulespecGroupHostsMonitoringRulesHostChecks,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupHostsMonitoringRulesNotifications as RulespecGroupHostsMonitoringRulesNotifications,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupHostsMonitoringRulesVarious as RulespecGroupHostsMonitoringRulesVarious,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupMonitoringAgents as RulespecGroupMonitoringAgents,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupMonitoringAgentsGenericOptions as RulespecGroupMonitoringAgentsGenericOptions,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupMonitoringConfiguration as RulespecGroupMonitoringConfiguration,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupMonitoringConfigurationNotifications as RulespecGroupMonitoringConfigurationNotifications,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupMonitoringConfigurationServiceChecks as RulespecGroupMonitoringConfigurationServiceChecks,
)
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupMonitoringConfigurationVarious as RulespecGroupMonitoringConfigurationVarious,
)
from cmk.gui.watolib.rulespecs import BinaryHostRulespec as BinaryHostRulespec
from cmk.gui.watolib.rulespecs import BinaryServiceRulespec as BinaryServiceRulespec
from cmk.gui.watolib.rulespecs import (
    CheckParameterRulespecWithItem as CheckParameterRulespecWithItem,
)
from cmk.gui.watolib.rulespecs import (
    CheckParameterRulespecWithoutItem as CheckParameterRulespecWithoutItem,
)
from cmk.gui.watolib.rulespecs import HostRulespec as HostRulespec
from cmk.gui.watolib.rulespecs import ManualCheckParameterRulespec as ManualCheckParameterRulespec
from cmk.gui.watolib.rulespecs import Rulespec as Rulespec
from cmk.gui.watolib.rulespecs import rulespec_group_registry as rulespec_group_registry
from cmk.gui.watolib.rulespecs import rulespec_registry as rulespec_registry
from cmk.gui.watolib.rulespecs import RulespecGroup as RulespecGroup
from cmk.gui.watolib.rulespecs import RulespecSubGroup as RulespecSubGroup
from cmk.gui.watolib.rulespecs import ServiceRulespec as ServiceRulespec
from cmk.gui.watolib.rulespecs import TimeperiodValuespec as TimeperiodValuespec
from cmk.gui.watolib.translation import HostnameTranslation as HostnameTranslation
from cmk.gui.watolib.translation import (
    ServiceDescriptionTranslation as ServiceDescriptionTranslation,
)
from cmk.gui.watolib.translation import translation_elements as translation_elements


def check_icmp_params() -> list[DictionaryEntry]:
    return [
        (
            "rta",
            Tuple(
                title=_("Round trip average"),
                elements=[
                    Float(title=_("Warning if above"), unit="ms", default_value=200.0),
                    Float(title=_("Critical if above"), unit="ms", default_value=500.0),
                ],
            ),
        ),
        (
            "loss",
            Tuple(
                title=_("Packet loss"),
                help=_(
                    "When the percentage of lost packets is equal or greater then "
                    "this level, then the according state is triggered. The default for critical "
                    "is 100%. That means that the check is only critical if <b>all</b> packets "
                    "are lost."
                ),
                elements=[
                    Percentage(title=_("Warning at"), default_value=80.0),
                    Percentage(title=_("Critical at"), default_value=100.0),
                ],
            ),
        ),
        (
            "packets",
            Integer(
                title=_("Number of packets"),
                help=_(
                    "Number ICMP echo request packets to send to the target host on each "
                    "check execution. All packets are sent directly on check execution. Afterwards "
                    "the check waits for the incoming packets."
                ),
                minvalue=1,
                maxvalue=20,
                default_value=5,
            ),
        ),
        (
            "timeout",
            Integer(
                title=_("Total timeout of check"),
                help=_(
                    "After this time (in seconds) the check is aborted, regardless "
                    "of how many packets have been received yet."
                ),
                minvalue=1,
            ),
        ),
    ]
