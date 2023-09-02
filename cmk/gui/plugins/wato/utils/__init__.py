#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for Setup internals and the Setup plugins"""

# TODO: More feature related splitting up would be better

import abc
import json
import re
import urllib.parse
from collections.abc import Callable, Mapping, Sequence
from typing import Any, cast, Literal

from livestatus import SiteConfiguration, SiteConfigurations, SiteId

import cmk.utils.plugin_registry
import cmk.utils.version as cmk_version
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.version import edition, Edition

from cmk.checkengine.checking import CheckPluginName

import cmk.gui.forms as forms
import cmk.gui.hooks as hooks
import cmk.gui.userdb as userdb
import cmk.gui.watolib.rulespecs as _rulespecs
import cmk.gui.weblib as weblib
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.hooks import request_memoize
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
from cmk.gui.utils.escaping import escape_to_html
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
from cmk.gui.watolib.attributes import IPMIParameters as IPMIParameters
from cmk.gui.watolib.attributes import SNMPCredentials as SNMPCredentials
from cmk.gui.watolib.check_mk_automations import (
    get_section_information as get_section_information_automation,
)
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
    host_attribute_topic_registry as host_attribute_topic_registry,
)
from cmk.gui.watolib.host_attributes import HostAttributeTopicAddress as HostAttributeTopicAddress
from cmk.gui.watolib.host_attributes import (
    HostAttributeTopicBasicSettings as HostAttributeTopicBasicSettings,
)
from cmk.gui.watolib.host_attributes import (
    HostAttributeTopicCustomAttributes as HostAttributeTopicCustomAttributes,
)
from cmk.gui.watolib.host_attributes import (
    HostAttributeTopicDataSources as HostAttributeTopicDataSources,
)
from cmk.gui.watolib.host_attributes import HostAttributeTopicHostTags as HostAttributeTopicHostTags
from cmk.gui.watolib.host_attributes import (
    HostAttributeTopicManagementBoard as HostAttributeTopicManagementBoard,
)
from cmk.gui.watolib.host_attributes import HostAttributeTopicMetaData as HostAttributeTopicMetaData
from cmk.gui.watolib.host_attributes import (
    HostAttributeTopicNetworkScan as HostAttributeTopicNetworkScan,
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


def PluginCommandLine() -> ValueSpec:
    def _validate_custom_check_command_line(value, varprefix):
        if "--pwstore=" in value:
            raise MKUserError(
                varprefix, _("You are not allowed to use passwords from the password store here.")
            )

    return TextInput(
        title=_("Command line"),
        help=_(
            "Please enter the complete shell command including path name and arguments to execute. "
            "If the plugin you like to execute is located in either <tt>~/local/lib/nagios/plugins</tt> "
            "or <tt>~/lib/nagios/plugins</tt> within your site directory, you can strip the path name and "
            "just configure the plugin file name as command <tt>check_foobar</tt>."
        )
        + monitoring_macro_help(),
        size="max",
        validate=_validate_custom_check_command_line,
    )


def monitoring_macro_help() -> str:
    return " " + _(
        "You can use monitoring macros here. The most important are: "
        "<ul>"
        "<li><tt>$HOSTADDRESS$</tt>: The IP address of the host</li>"
        "<li><tt>$HOSTNAME$</tt>: The name of the host</li>"
        "<li><tt>$_HOSTTAGS$</tt>: List of host tags</li>"
        "<li><tt>$_HOSTADDRESS_4$</tt>: The IPv4 address of the host</li>"
        "<li><tt>$_HOSTADDRESS_6$</tt>: The IPv6 address of the host</li>"
        "<li><tt>$_HOSTADDRESS_FAMILY$</tt>: The primary address family of the host</li>"
        "</ul>"
        "All custom attributes defined for the host are available as <tt>$_HOST[VARNAME]$</tt>. "
        "Replace <tt>[VARNAME]</tt> with the <i>upper case</i> name of your variable. "
        "For example, a host attribute named <tt>foo</tt> with the value <tt>bar</tt> would result in "
        "the macro <tt>$_HOSTFOO$</tt> being replaced with <tt>bar</tt> "
    )


def notification_macro_help() -> str:
    return _(
        "Here you are allowed to use all macros that are defined in the "
        "notification context.<br>"
        "The most important are:"
        "<ul>"
        "<li><tt>$HOSTNAME$</li>"
        "<li><tt>$SERVICEDESC$</li>"
        "<li><tt>$SERVICESHORTSTATE$</li>"
        "<li><tt>$SERVICEOUTPUT$</li>"
        "<li><tt>$LONGSERVICEOUTPUT$</li>"
        "<li><tt>$SERVICEPERFDATA$</li>"
        "<li><tt>$EVENT_TXT$</li>"
        "</ul>"
    )


def UserIconOrAction(title: str, help: str) -> DropdownChoice:  # pylint: disable=redefined-builtin
    empty_text = (
        _(
            "In order to be able to choose actions here, you need to "
            '<a href="%s">define your own actions</a>.'
        )
        % "wato.py?mode=edit_configvar&varname=user_icons_and_actions"
    )

    return DropdownChoice(
        title=title,
        choices=_list_user_icons_and_actions,
        empty_text=empty_text,
        help=help + " " + empty_text,
    )


def _list_user_icons_and_actions() -> DropdownChoiceEntries:
    choices = []
    for key, action in active_config.user_icons_and_actions.items():
        label = key
        if "title" in action:
            label += " - " + action["title"]
        if "url" in action:
            label += " (" + action["url"][0] + ")"

        choices.append((key, label))
    return sorted(choices, key=lambda x: x[1])


_allowed_schemes = frozenset({"http", "https", "socks4", "socks4a", "socks5", "socks5h"})


def HTTPProxyReference(  # type: ignore[no-untyped-def]
    allowed_schemes=_allowed_schemes,
) -> ValueSpec:
    """Use this valuespec in case you want the user to configure a HTTP proxy
    The configured value is is used for preparing requests to work in a proxied environment."""

    def _global_proxy_choices() -> DropdownChoiceEntries:
        settings = _ConfigDomainCore().load()
        return [
            (p["ident"], p["title"])
            for p in settings.get("http_proxies", {}).values()
            if urllib.parse.urlparse(p["proxy_url"]).scheme in allowed_schemes
        ]

    return CascadingDropdown(
        title=_("HTTP proxy"),
        default_value=("environment", "environment"),
        choices=[
            (
                "environment",
                _("Use from environment"),
                FixedValue(
                    value="environment",
                    help=_(
                        "Use the proxy settings from the environment variables. The variables <tt>NO_PROXY</tt>, "
                        "<tt>HTTP_PROXY</tt> and <tt>HTTPS_PROXY</tt> are taken into account during execution. "
                        "Have a look at the python requests module documentation for further information. Note "
                        "that these variables must be defined as a site-user in ~/etc/environment and that "
                        "this might affect other notification methods which also use the requests module."
                    ),
                    totext=_(
                        "Use proxy settings from the process environment. This is the default."
                    ),
                ),
            ),
            (
                "no_proxy",
                _("Connect without proxy"),
                FixedValue(
                    value=None,
                    totext=_("Connect directly to the destination instead of using a proxy."),
                ),
            ),
            (
                "global",
                _("Use globally configured proxy"),
                DropdownChoice(
                    choices=_global_proxy_choices,
                    sorted=True,
                ),
            ),
            ("url", _("Use explicit proxy settings"), HTTPProxyInput(allowed_schemes)),
        ],
        sorted=False,
    )


def HTTPProxyInput(allowed_schemes=_allowed_schemes):
    """Use this valuespec in case you want the user to input a HTTP proxy setting"""
    return Url(
        title=_("Proxy URL"),
        default_scheme="http",
        allowed_schemes=allowed_schemes,
    )


@rulespec_group_registry.register
class RulespecGroupDiscoveryCheckParameters(RulespecGroup):
    @property
    def name(self) -> str:
        return "checkparams"

    @property
    def title(self) -> str:
        return _("Service discovery rules")

    @property
    def help(self):
        return _(
            "Rules that influence the discovery of services. These rules "
            "allow, for example, the execution of a periodic service "
            "discovery or the deactivation of check plugins and services. "
            "Additionally, the discovery of individual check plugins like "
            "for example the interface check plugin can "
            "be customized."
        )


@rulespec_group_registry.register
class RulespecGroupCheckParametersNetworking(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "networking"

    @property
    def title(self) -> str:
        return _("Networking")


@rulespec_group_registry.register
class RulespecGroupCheckParametersStorage(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "storage"

    @property
    def title(self) -> str:
        return _("Storage, Filesystems and Files")


@rulespec_group_registry.register
class RulespecGroupCheckParametersOperatingSystem(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "os"

    @property
    def title(self) -> str:
        return _("Operating System Resources")


@rulespec_group_registry.register
class RulespecGroupCheckParametersPrinters(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "printers"

    @property
    def title(self) -> str:
        return _("Printers")


@rulespec_group_registry.register
class RulespecGroupCheckParametersEnvironment(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "environment"

    @property
    def title(self) -> str:
        return _("Temperature, Humidity, Electrical Parameters, etc.")


@rulespec_group_registry.register
class RulespecGroupCheckParametersApplications(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "applications"

    @property
    def title(self) -> str:
        return _("Applications, Processes & Services")


@rulespec_group_registry.register
class RulespecGroupCheckParametersVirtualization(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "virtualization"

    @property
    def title(self) -> str:
        return _("Virtualization")


@rulespec_group_registry.register
class RulespecGroupCheckParametersHardware(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "hardware"

    @property
    def title(self) -> str:
        return _("Hardware, BIOS")


@rulespec_group_registry.register
class RulespecGroupCheckParametersDiscovery(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupDiscoveryCheckParameters

    @property
    def sub_group_name(self) -> str:
        return "discovery"

    @property
    def title(self) -> str:
        return _("Discovery of individual services")


# The following function looks like a value spec and in fact
# can be used like one (but take no parameters)
def PredictiveLevels(
    default_difference: tuple[float, float] = (2.0, 4.0), unit: str = ""
) -> Dictionary:
    dif = default_difference
    unitname = unit
    if unitname:
        unitname += " "

    return Dictionary(
        title=_("Predictive Levels (only on CMC)"),
        optional_keys=[
            "weight",
            "levels_upper",
            "levels_upper_min",
            "levels_lower",
            "levels_lower_max",
        ],
        default_keys=["levels_upper"],
        columns=1,
        elements=[
            (
                "period",
                DropdownChoice(
                    title=_("Base prediction on"),
                    choices=[
                        ("wday", _("Day of the week (1-7, 1 is Monday)")),
                        ("day", _("Day of the month (1-31)")),
                        ("hour", _("Hour of the day (0-23)")),
                        ("minute", _("Minute of the hour (0-59)")),
                    ],
                ),
            ),
            (
                "horizon",
                Integer(
                    title=_("Time horizon"),
                    unit=_("days"),
                    minvalue=1,
                    default_value=90,
                ),
            ),
            # ( "weight",
            #   Percentage(
            #       title = _("Raise weight of recent time"),
            #       label = _("by"),
            #       default_value = 0,
            # )),
            (
                "levels_upper",
                CascadingDropdown(
                    title=_("Dynamic levels - upper bound"),
                    choices=[
                        (
                            "absolute",
                            _("Absolute difference from prediction"),
                            Tuple(
                                elements=[
                                    Float(
                                        title=_("Warning at"),
                                        unit=unitname + _("above predicted value"),
                                        default_value=dif[0],
                                    ),
                                    Float(
                                        title=_("Critical at"),
                                        unit=unitname + _("above predicted value"),
                                        default_value=dif[1],
                                    ),
                                ]
                            ),
                        ),
                        (
                            "relative",
                            _("Relative difference from prediction"),
                            Tuple(
                                elements=[
                                    Percentage(
                                        title=_("Warning at"),
                                        # xgettext: no-python-format
                                        unit=_("% above predicted value"),
                                        default_value=10,
                                    ),
                                    Percentage(
                                        title=_("Critical at"),
                                        # xgettext: no-python-format
                                        unit=_("% above predicted value"),
                                        default_value=20,
                                    ),
                                ]
                            ),
                        ),
                        (
                            "stdev",
                            _("In relation to standard deviation"),
                            Tuple(
                                elements=[
                                    Float(
                                        title=_("Warning at"),
                                        unit=_(
                                            "times the standard deviation above the predicted value"
                                        ),
                                        default_value=2.0,
                                    ),
                                    Float(
                                        title=_("Critical at"),
                                        unit=_(
                                            "times the standard deviation above the predicted value"
                                        ),
                                        default_value=4.0,
                                    ),
                                ]
                            ),
                        ),
                    ],
                ),
            ),
            (
                "levels_upper_min",
                Tuple(
                    title=_("Limit for upper bound dynamic levels"),
                    help=_(
                        "Regardless of how the dynamic levels upper bound are computed according to the prediction: "
                        "the will never be set below the following limits. This avoids false alarms "
                        "during times where the predicted levels would be very low."
                    ),
                    elements=[
                        Float(title=_("Warning level is at least"), unit=unitname),
                        Float(title=_("Critical level is at least"), unit=unitname),
                    ],
                ),
            ),
            (
                "levels_lower",
                CascadingDropdown(
                    title=_("Dynamic levels - lower bound"),
                    choices=[
                        (
                            "absolute",
                            _("Absolute difference from prediction"),
                            Tuple(
                                elements=[
                                    Float(
                                        title=_("Warning at"),
                                        unit=unitname + _("below predicted value"),
                                        default_value=2.0,
                                    ),
                                    Float(
                                        title=_("Critical at"),
                                        unit=unitname + _("below predicted value"),
                                        default_value=4.0,
                                    ),
                                ]
                            ),
                        ),
                        (
                            "relative",
                            _("Relative difference from prediction"),
                            Tuple(
                                elements=[
                                    Percentage(
                                        title=_("Warning at"),
                                        # xgettext: no-python-format
                                        unit=_("% below predicted value"),
                                        default_value=10,
                                    ),
                                    Percentage(
                                        title=_("Critical at"),
                                        # xgettext: no-python-format
                                        unit=_("% below predicted value"),
                                        default_value=20,
                                    ),
                                ]
                            ),
                        ),
                        (
                            "stdev",
                            _("In relation to standard deviation"),
                            Tuple(
                                elements=[
                                    Float(
                                        title=_("Warning at"),
                                        unit=_(
                                            "times the standard deviation below the predicted value"
                                        ),
                                        default_value=2.0,
                                    ),
                                    Float(
                                        title=_("Critical at"),
                                        unit=_(
                                            "times the standard deviation below the predicted value"
                                        ),
                                        default_value=4.0,
                                    ),
                                ]
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )


# To be used as ValueSpec for levels on numeric values, with
# prediction
def Levels(
    help: str | None = None,  # pylint: disable=redefined-builtin
    default_levels: tuple[float, float] = (0.0, 0.0),
    default_difference: tuple[float, float] = (0.0, 0.0),
    default_value: tuple[float, float] | None = None,
    title: str | None = None,
    unit: str = "",
) -> Alternative:
    def match_levels_alternative(v: dict[Any, Any] | tuple[Any, Any]) -> int:
        if isinstance(v, dict):
            return 2
        if isinstance(v, tuple) and v != (None, None):
            return 1
        return 0

    if not isinstance(unit, str):
        raise ValueError(f"illegal unit for Levels: {unit}, expected a string")

    if default_value is None:
        default_value = default_levels

    elements: Sequence[ValueSpec[Any]] = [
        FixedValue(
            value=None,
            title=_("No Levels"),
            totext=_("Do not impose levels, always be OK"),
        ),
        Tuple(
            title=_("Fixed Levels"),
            elements=[
                Float(
                    unit=unit,
                    title=_("Warning at"),
                    default_value=default_levels[0],
                    allow_int=True,
                ),
                Float(
                    unit=unit,
                    title=_("Critical at"),
                    default_value=default_levels[1],
                    allow_int=True,
                ),
            ],
        ),
        PredictiveLevels(default_difference=default_difference, unit=unit),
    ]

    return Alternative(
        title=title,
        help=help,
        elements=elements,
        match=match_levels_alternative,
        default_value=default_value,
    )


# TODO: Kept for compatibility with pre-1.6 Setup plugins
def register_hook(name, func):
    hooks.register_from_plugin(name, func)


@request_memoize()
def get_section_information() -> Mapping[str, Mapping[str, str]]:
    return get_section_information_automation().section_infos


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
