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
from contextlib import AbstractContextManager, nullcontext
from typing import Any, cast, Literal

from livestatus import SiteConfiguration, SiteConfigurations, SiteId

import cmk.utils.plugin_registry
import cmk.utils.version as cmk_version
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.tags import TagGroupID, TagID
from cmk.utils.version import edition, Edition

from cmk.checkengine.checking import CheckPluginName

import cmk.gui.forms as forms
import cmk.gui.hooks as hooks
import cmk.gui.userdb as userdb
import cmk.gui.watolib.rulespecs as _rulespecs
import cmk.gui.weblib as weblib
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.groups import (
    GroupSpecs,
    load_contact_group_information,
    load_host_group_information,
    load_service_group_information,
)
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _u
from cmk.gui.logged_in import user
from cmk.gui.pages import page_registry
from cmk.gui.permissions import permission_section_registry, PermissionSection
from cmk.gui.plugins.wato.utils.main_menu import MainMenu as MainMenu
from cmk.gui.plugins.wato.utils.main_menu import MainModuleTopicAgents as MainModuleTopicAgents
from cmk.gui.plugins.wato.utils.main_menu import MainModuleTopicBI as MainModuleTopicBI
from cmk.gui.plugins.wato.utils.main_menu import MainModuleTopicEvents as MainModuleTopicEvents
from cmk.gui.plugins.wato.utils.main_menu import MainModuleTopicExporter as MainModuleTopicExporter
from cmk.gui.plugins.wato.utils.main_menu import MainModuleTopicGeneral as MainModuleTopicGeneral
from cmk.gui.plugins.wato.utils.main_menu import MainModuleTopicHosts as MainModuleTopicHosts
from cmk.gui.plugins.wato.utils.main_menu import (
    MainModuleTopicMaintenance as MainModuleTopicMaintenance,
)
from cmk.gui.plugins.wato.utils.main_menu import MainModuleTopicServices as MainModuleTopicServices
from cmk.gui.plugins.wato.utils.main_menu import MainModuleTopicUsers as MainModuleTopicUsers
from cmk.gui.plugins.wato.utils.main_menu import register_modules as register_modules
from cmk.gui.plugins.wato.utils.main_menu import WatoModule as WatoModule
from cmk.gui.site_config import is_wato_slave_site as is_wato_slave_site
from cmk.gui.type_defs import Choices as Choices
from cmk.gui.type_defs import ChoiceText as ChoiceText
from cmk.gui.user_sites import get_activation_site_choices, get_configured_site_choices
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
from cmk.gui.valuespec import ElementSelection as ElementSelection
from cmk.gui.valuespec import FixedValue as FixedValue
from cmk.gui.valuespec import Float as Float
from cmk.gui.valuespec import Integer as Integer
from cmk.gui.valuespec import JSONValue as JSONValue
from cmk.gui.valuespec import Labels as Labels
from cmk.gui.valuespec import ListChoice as ListChoice
from cmk.gui.valuespec import ListOf as ListOf
from cmk.gui.valuespec import ListOfMultiple as ListOfMultiple
from cmk.gui.valuespec import ListOfStrings as ListOfStrings
from cmk.gui.valuespec import Migrate as Migrate
from cmk.gui.valuespec import MigrateNotUpdated as MigrateNotUpdated
from cmk.gui.valuespec import MonitoredHostname as MonitoredHostname
from cmk.gui.valuespec import Password as Password
from cmk.gui.valuespec import Percentage as Percentage
from cmk.gui.valuespec import RegExp as RegExp
from cmk.gui.valuespec import TextInput as TextInput
from cmk.gui.valuespec import Transform as Transform
from cmk.gui.valuespec import Tuple as Tuple
from cmk.gui.valuespec import Url as Url
from cmk.gui.valuespec import ValueSpec as ValueSpec
from cmk.gui.valuespec import ValueSpecHelp as ValueSpecHelp
from cmk.gui.valuespec import ValueSpecText as ValueSpecText
from cmk.gui.watolib.attributes import IPMIParameters as IPMIParameters
from cmk.gui.watolib.attributes import SNMPCredentials as SNMPCredentials
from cmk.gui.watolib.check_mk_automations import get_check_information_cached
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
from cmk.gui.watolib.password_store import passwordstore_choices as passwordstore_choices
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
from cmk.gui.watolib.users import notification_script_title


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


# TODO: Refactor this and all other children of ElementSelection() to base on
#       DropdownChoice(). Then remove ElementSelection()
class _GroupSelection(ElementSelection):
    def __init__(
        self,
        what: str,
        choices: Callable[[], Choices],
        no_selection: ChoiceText | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault(
            "empty_text",
            _(
                "You have not defined any %s group yet. Please "
                '<a href="wato.py?mode=edit_%s_group">create</a> at least one first.'
            )
            % (what, what),
        )
        super().__init__(**kwargs)
        self._what = what
        self._choices = choices
        self._no_selection = no_selection

    def get_elements(self):
        elements = self._choices()
        if self._no_selection:
            # Beware: ElementSelection currently can only handle string
            # keys, so we cannot take 'None' as a value.
            elements.append(("", self._no_selection))
        return dict(elements)


def ContactGroupSelection(**kwargs: Any) -> ElementSelection:
    """Select a single contact group"""
    return _GroupSelection("contact", choices=_sorted_contact_group_choices, **kwargs)


def ServiceGroupSelection(**kwargs: Any) -> ElementSelection:
    """Select a single service group"""
    return _GroupSelection("service", choices=_sorted_service_group_choices, **kwargs)


def HostGroupSelection(**kwargs: Any) -> ElementSelection:
    """Select a single host group"""
    return _GroupSelection("host", choices=_sorted_host_group_choices, **kwargs)


def ContactGroupChoice(**kwargs: Any) -> DualListChoice:
    """Select multiple contact groups"""
    return DualListChoice(choices=_sorted_contact_group_choices, **kwargs)  # type: ignore[arg-type]


def ServiceGroupChoice(**kwargs: Any) -> DualListChoice:
    """Select multiple service groups"""
    return DualListChoice(choices=_sorted_service_group_choices, **kwargs)  # type: ignore[arg-type]


def HostGroupChoice(**kwargs: Any) -> DualListChoice:
    """Select multiple host groups"""
    return DualListChoice(choices=_sorted_host_group_choices, **kwargs)  # type: ignore[arg-type]


@request_memoize()
def _sorted_contact_group_choices() -> Choices:
    return _group_choices(load_contact_group_information())


@request_memoize()
def _sorted_service_group_choices() -> Choices:
    return _group_choices(load_service_group_information())


@request_memoize()
def _sorted_host_group_choices() -> Choices:
    return _group_choices(load_host_group_information())


def _group_choices(group_information: GroupSpecs) -> Choices:
    return sorted(
        [(k, t["alias"] and t["alias"] or k) for (k, t) in group_information.items()],
        key=lambda x: x[1].lower(),
    )


def IndividualOrStoredPassword(  # pylint: disable=redefined-builtin
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    allow_empty: bool = True,
    size: int = 25,
) -> CascadingDropdown:
    """ValueSpec for a password that can be entered directly or selected from a password store

    One should look into using :func:`password_store.extract` to translate the reference to the
    actual password.
    """
    return CascadingDropdown(
        title=title,
        help=help,
        choices=[
            (
                "password",
                _("Explicit"),
                Password(
                    allow_empty=allow_empty,
                    size=size,
                ),
            ),
            (
                "store",
                _("From password store"),
                DropdownChoice(
                    choices=passwordstore_choices,
                    sorted=True,
                    invalid_choice="complain",
                    invalid_choice_title=_("Password does not exist or using not permitted"),
                    invalid_choice_error=_(
                        "The configured password has either be removed or you "
                        "are not permitted to use this password. Please choose "
                        "another one."
                    ),
                ),
            ),
        ],
        orientation="horizontal",
    )


PasswordFromStore = IndividualOrStoredPassword  # CMK-12228


def MigrateToIndividualOrStoredPassword(  # pylint: disable=redefined-builtin
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    allow_empty: bool = True,
    size: int = 25,
) -> Migrate:
    return Migrate(
        valuespec=IndividualOrStoredPassword(
            title=title,
            help=help,
            allow_empty=allow_empty,
            size=size,
        ),
        migrate=lambda v: ("password", v) if not isinstance(v, tuple) else v,
    )


def MigrateNotUpdatedToIndividualOrStoredPassword(  # pylint: disable=redefined-builtin
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    allow_empty: bool = True,
    size: int = 25,
) -> MigrateNotUpdated:
    return MigrateNotUpdated(
        valuespec=IndividualOrStoredPassword(
            title=title,
            help=help,
            allow_empty=allow_empty,
            size=size,
        ),
        migrate=lambda v: ("password", v) if not isinstance(v, tuple) else v,
    )


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


def register_check_parameters(
    subgroup,
    checkgroup,
    title,
    valuespec,
    itemspec,
    match_type,
    has_inventory=True,
    register_static_check=True,
    deprecated=False,
):
    """Legacy registration of check parameters"""
    if valuespec and isinstance(valuespec, Dictionary) and match_type != "dict":
        raise MKGeneralException(
            "Check parameter definition for %s has type Dictionary, but match_type %s"
            % (checkgroup, match_type)
        )

    if not valuespec:
        raise NotImplementedError()

    # Added during 1.6 development for easier transition. Convert all legacy subgroup
    # parameters (which are either str/unicode to group classes
    if isinstance(subgroup, str):
        subgroup = _rulespecs.get_rulegroup("checkparams/" + subgroup).__class__

    # Register rule for discovered checks
    if has_inventory:
        kwargs = {
            "group": subgroup,
            "title": lambda: title,
            "match_type": match_type,
            "is_deprecated": deprecated,
            "parameter_valuespec": lambda: valuespec,
            "check_group_name": checkgroup,
            "create_manual_check": register_static_check,
        }

        if itemspec:
            rulespec_registry.register(
                CheckParameterRulespecWithItem(item_spec=lambda: itemspec, **kwargs)
            )
        else:
            rulespec_registry.register(CheckParameterRulespecWithoutItem(**kwargs))

    if not (valuespec and has_inventory) and register_static_check:
        raise MKGeneralException(
            "Sorry, registering manual check parameters without discovery "
            "check parameters is not supported anymore using the old API. "
            "Please register the manual check rulespec using the new API. "
            "Checkgroup: %s" % checkgroup
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


def valuespec_check_plugin_selection(
    *,
    title: str,
    help_: str,
) -> Transform:
    return Transform(
        valuespec=Dictionary(
            title=title,
            help=help_,
            elements=[
                ("host", _CheckTypeHostSelection(title=_("Checks on regular hosts"))),
                ("mgmt", _CheckTypeMgmtSelection(title=_("Checks on management boards"))),
            ],
            optional_keys=["mgmt"],
        ),
        # omit empty mgmt key
        to_valuespec=lambda list_: {
            k: v
            for k, v in (
                ("host", [name for name in list_ if not name.startswith("mgmt_")]),
                ("mgmt", [name[5:] for name in list_ if name.startswith("mgmt_")]),
            )
            if v or k == "host"
        },
        from_valuespec=lambda dict_: dict_["host"] + [f"mgmt_{n}" for n in dict_.get("mgmt", ())],
    )


class _CheckTypeHostSelection(DualListChoice):
    def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(rows=25, **kwargs)

    def get_elements(self):
        checks = get_check_information_cached()
        return [
            (str(cn), (str(cn) + " - " + c["title"])[:60])
            for (cn, c) in checks.items()
            # filter out plugins implemented *explicitly* for management boards
            if not cn.is_management_name()
        ]


class _CheckTypeMgmtSelection(DualListChoice):
    def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(rows=25, **kwargs)

    def get_elements(self):
        checks = get_check_information_cached()
        return [
            (str(cn.create_basic_name()), (str(cn) + " - " + c["title"])[:60])
            for (cn, c) in checks.items()
        ]


# TODO: Kept for compatibility with pre-1.6 Setup plugins
def register_hook(name, func):
    hooks.register_from_plugin(name, func)


class NotificationParameter(abc.ABC):
    @property
    @abc.abstractmethod
    def ident(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def spec(self) -> Dictionary:
        raise NotImplementedError()


class NotificationParameterRegistry(
    cmk.utils.plugin_registry.Registry[type[NotificationParameter]]
):
    def plugin_name(self, instance):
        return instance().ident

    # TODO: Make this registration_hook actually take an instance. Atm it takes a class and
    #       instantiates it
    def registration_hook(self, instance):
        plugin = instance()

        script_title = notification_script_title(plugin.ident)

        valuespec = plugin.spec
        # TODO: Cleanup this hack
        valuespec._title = _("Call with the following parameters:")

        _rulespecs.register_rule(
            rulespec_group_registry["monconf/notifications"],
            RuleGroup.NotificationParameters(plugin.ident),
            valuespec,
            _("Parameters for %s") % script_title,
            itemtype=None,
            match="dict",
        )


notification_parameter_registry = NotificationParameterRegistry()


# TODO: Kept for pre 1.6 plugin compatibility
def register_notification_parameters(scriptname, valuespec):
    parameter_class = type(
        "NotificationParameter%s" % scriptname.title(),
        (NotificationParameter,),
        {
            "ident": scriptname,
            "spec": valuespec,
        },
    )
    notification_parameter_registry.register(parameter_class)


class HostTagCondition(ValueSpec[Sequence[str]]):
    """ValueSpec for editing a tag-condition"""

    def render_input(self, varprefix: str, value: Sequence[str]) -> None:
        self._render_condition_editor(varprefix, value)

    def from_html_vars(self, varprefix: str) -> Sequence[str]:
        return self._get_tag_conditions(varprefix)

    def _get_tag_conditions(self, varprefix: str) -> Sequence[str]:
        """Retrieve current tag condition settings from HTML variables"""

        def gettagvalue(tgid: TagGroupID) -> TagID | None:
            v = request.var(varprefix + "tagvalue_" + tgid)
            if v is None:
                return None
            return TagID(v)

        if varprefix:
            varprefix += "_"

        # Main tags
        tag_list = []
        for tag_group in active_config.tags.tag_groups:
            if tag_group.is_checkbox_tag_group:
                tagvalue = tag_group.default_value
            else:
                tagvalue = gettagvalue(tag_group.id)

            # Not all tags are submitted, see cmk.gui.forms.remove_unused_vars.
            # So simply skip None values.
            if tagvalue is None:
                continue

            mode = request.var(varprefix + "tag_" + tag_group.id)
            if mode == "is":
                tag_list.append(tagvalue)
            elif mode == "isnot":
                tag_list.append(TagID("!" + tagvalue))

        # Auxiliary tags
        for aux_tag in active_config.tags.aux_tag_list.get_tags():
            mode = request.var(varprefix + "auxtag_" + aux_tag.id)
            if mode == "is":
                tag_list.append(aux_tag.id)
            elif mode == "isnot":
                tag_list.append(TagID("!" + aux_tag.id))

        return tag_list

    def canonical_value(self) -> Sequence[str]:
        return []

    def value_to_html(self, value: Sequence[str]) -> ValueSpecText:
        return "|".join(value)

    def validate_datatype(self, value: Sequence[str], varprefix: str) -> None:
        if not isinstance(value, list):
            raise MKUserError(
                varprefix, _("The list of host tags must be a list, but is %r") % type(value)
            )
        for x in value:
            if not isinstance(x, str):
                raise MKUserError(
                    varprefix,
                    _("The list of host tags must only contain strings but also contains %r") % x,
                )

    def _render_condition_editor(self, varprefix: str, tag_specs: Sequence[str]) -> None:
        """Render HTML input fields for editing a tag based condition"""
        if varprefix:
            varprefix += "_"

        if not active_config.tags.get_tag_ids():
            html.write_text(_('You have not configured any <a href="wato.py?mode=tags">tags</a>.'))
            return

        tag_groups_by_topic = dict(active_config.tags.get_tag_groups_by_topic())
        aux_tags_by_topic = dict(active_config.tags.get_aux_tags_by_topic())

        all_topics = active_config.tags.get_topic_choices()
        make_foldable = len(all_topics) > 1

        for topic_id, topic_title in all_topics:
            container: AbstractContextManager[bool] = (
                foldable_container(
                    treename="topic",
                    id_=varprefix + topic_title,
                    isopen=True,
                    title=_u(topic_title),
                )
                if make_foldable
                else nullcontext(False)
            )
            with container:
                html.open_table(class_=["hosttags"])

                for tag_group in tag_groups_by_topic.get(topic_id, []):
                    html.open_tr()
                    html.td("%s: &nbsp;" % _u(tag_group.title or ""), class_="title")

                    choices = tag_group.get_tag_choices()
                    default_tag, deflt = self._current_tag_setting(choices, tag_specs)
                    self._tag_condition_dropdown(varprefix, "tag", deflt, tag_group.id)
                    if tag_group.is_checkbox_tag_group:
                        html.write_text(" " + _("set"))
                    else:
                        html.dropdown(
                            varprefix + "tagvalue_" + tag_group.id,
                            [(t[0], _u(t[1])) for t in choices if t[0] is not None],
                            deflt=default_tag,
                        )

                    html.close_div()
                    html.close_td()
                    html.close_tr()

                for aux_tag in aux_tags_by_topic.get(topic_id, []):
                    html.open_tr()
                    html.td("%s: &nbsp;" % _u(aux_tag.title), class_="title")
                    default_tag, deflt = self._current_tag_setting(
                        [(aux_tag.id, _u(aux_tag.title))], tag_specs
                    )
                    self._tag_condition_dropdown(varprefix, "auxtag", deflt, aux_tag.id)
                    html.write_text(" " + _("set"))
                    html.close_div()
                    html.close_td()
                    html.close_tr()

                html.close_table()

    def _current_tag_setting(
        self, choices: Sequence[tuple[str | None, str]], tag_specs: Sequence[str]
    ) -> tuple[Any, str]:
        """Determine current (default) setting of tag by looking into tag_specs (e.g. [ "snmp", "!tcp", "test" ] )"""
        default_tag = None
        ignore = True
        for t in tag_specs:
            if t[0] == "!":
                n = True
                t = t[1:]
            else:
                n = False
            if t in [x[0] for x in choices]:
                default_tag = t
                ignore = False
                negate = n
        if ignore:
            deflt = "ignore"
        elif negate:
            deflt = "isnot"
        else:
            deflt = "is"
        return default_tag, deflt

    def _tag_condition_dropdown(self, varprefix: str, tagtype: str, deflt: str, id_: str) -> None:
        """Show dropdown with "is/isnot/ignore" and beginning of div that is switched visible by is/isnot"""
        html.open_td()
        dropdown_id = varprefix + tagtype + "_" + id_
        onchange = f"cmk.valuespecs.toggle_tag_dropdown(this, '{varprefix}tag_sel_{id_}');"
        choices: Choices = [
            ("ignore", _("ignore")),
            ("is", _("is")),
            ("isnot", _("isnot")),
        ]
        html.dropdown(dropdown_id, choices, deflt=deflt, onchange=onchange)
        html.close_td()

        html.open_td(class_="tag_sel")
        if html.form_submitted():
            div_is_open = request.var(dropdown_id, "ignore") != "ignore"
        else:
            div_is_open = deflt != "ignore"
        html.open_div(
            id_=f"{varprefix}tag_sel_{id_}",
            style="display: none;" if not div_is_open else None,
        )

    def mask(self, value: Sequence[str]) -> Sequence[str]:
        return value

    def value_to_json(self, value: Sequence[str]) -> JSONValue:
        raise NotImplementedError()  # FIXME! Violates LSP!

    def value_from_json(self, json_value: JSONValue) -> Sequence[str]:
        raise NotImplementedError()  # FIXME! Violates LSP!


def multifolder_host_rule_match_conditions() -> list[DictionaryEntry]:
    return [
        site_rule_match_condition(only_sites_with_replication=True),
        _multi_folder_rule_match_condition(),
    ] + common_host_rule_match_conditions()


def site_rule_match_condition(only_sites_with_replication: bool) -> DictionaryEntry:
    return (
        "match_site",
        DualListChoice(
            title=_("Match sites"),
            help=_("This condition makes the rule match only hosts of the selected sites."),
            choices=get_activation_site_choices
            if only_sites_with_replication
            else get_configured_site_choices,
        ),
    )


def _multi_folder_rule_match_condition() -> DictionaryEntry:
    return (
        "match_folders",
        ListOf(
            valuespec=FullPathFolderChoice(
                title=_("Folder"),
                help=_(
                    "This condition makes the rule match only hosts that are managed "
                    "via Setup and that are contained in this folder - either directly "
                    "or in one of its subfolders."
                ),
            ),
            add_label=_("Add additional folder"),
            title=_("Match folders"),
            movable=False,
        ),
    )


def common_host_rule_match_conditions() -> list[DictionaryEntry]:
    return [
        ("match_hosttags", HostTagCondition(title=_("Match host tags"))),
        (
            "match_hostlabels",
            Labels(
                world=Labels.World.CORE,
                title=_("Match host labels"),
                help=_("Use this condition to select hosts based on the configured host labels."),
            ),
        ),
        (
            "match_hostgroups",
            HostGroupChoice(
                title=_("Match host groups"),
                help=_("The host must be in one of the selected host groups"),
                allow_empty=False,
            ),
        ),
        (
            "match_hosts",
            ListOfStrings(
                valuespec=MonitoredHostname(),  # type: ignore[arg-type]  # should be Valuespec[str]
                title=_("Match hosts"),
                size=24,
                orientation="horizontal",
                allow_empty=False,
                empty_text=_(
                    "Please specify at least one host. Disable the option if you want to allow all hosts."
                ),
            ),
        ),
        (
            "match_exclude_hosts",
            ListOfStrings(
                valuespec=MonitoredHostname(),  # type: ignore[arg-type]  # should be Valuespec[str]
                title=_("Exclude hosts"),
                size=24,
                orientation="horizontal",
            ),
        ),
    ]


class FullPathFolderChoice(DropdownChoice):
    def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        kwargs["choices"] = folder_tree().folder_choices_fulltitle
        kwargs.setdefault("title", _("Folder"))
        DropdownChoice.__init__(self, **kwargs)


class FolderChoice(DropdownChoice):
    def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        kwargs["choices"] = folder_tree().folder_choices
        kwargs.setdefault("title", _("Folder"))
        DropdownChoice.__init__(self, **kwargs)


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
