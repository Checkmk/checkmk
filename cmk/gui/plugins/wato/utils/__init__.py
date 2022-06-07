#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for WATO internals and the WATO plugins"""

# TODO: More feature related splitting up would be better

import abc
import json
import re
import subprocess
import urllib.parse
from contextlib import nullcontext
from typing import Any, Callable, cast, ContextManager, Dict, List, Mapping
from typing import Optional as _Optional
from typing import Sequence
from typing import Tuple as _Tuple
from typing import Type, Union

from livestatus import SiteConfiguration, SiteConfigurations, SiteId

import cmk.utils.plugin_registry
from cmk.utils.type_defs import CheckPluginName

import cmk.gui.backup as backup
import cmk.gui.forms as forms
import cmk.gui.hooks as hooks
import cmk.gui.mkeventd
import cmk.gui.userdb as userdb
import cmk.gui.watolib.host_attributes as _host_attributes
import cmk.gui.watolib.hosts_and_folders as _hosts_and_folders
import cmk.gui.watolib.rulespecs as _rulespecs
import cmk.gui.watolib.timeperiods as _timeperiods
import cmk.gui.weblib as weblib
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKGeneralException, MKUserError
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
from cmk.gui.plugins.wato.utils.base_modes import (  # noqa: F401 # pylint: disable=unused-import
    mode_registry,
    mode_url,
    redirect,
    WatoMode,
)
from cmk.gui.plugins.wato.utils.html_elements import (  # noqa: F401 # pylint: disable=unused-import
    search_form,
)
from cmk.gui.plugins.wato.utils.main_menu import (  # noqa: F401 # pylint: disable=unused-import
    ABCMainModule,
    main_module_registry,
    MainMenu,
    MainModuleTopic,
    MainModuleTopicAgents,
    MainModuleTopicBI,
    MainModuleTopicEvents,
    MainModuleTopicExporter,
    MainModuleTopicGeneral,
    MainModuleTopicHosts,
    MainModuleTopicMaintenance,
    MainModuleTopicServices,
    MainModuleTopicUsers,
    MenuItem,
    register_modules,
    WatoModule,
)
from cmk.gui.plugins.wato.utils.simple_modes import (  # noqa: F401 # pylint: disable=unused-import
    SimpleEditMode,
    SimpleListMode,
    SimpleModeType,
)
from cmk.gui.site_config import (  # noqa: F401 # pylint: disable=unused-import
    get_site_config,
    is_wato_slave_site,
)
from cmk.gui.type_defs import Choices
from cmk.gui.user_sites import get_activation_site_choices
from cmk.gui.utils.escaping import escape_to_html
from cmk.gui.utils.flashed_messages import flash  # noqa: F401 # pylint: disable=unused-import
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_link  # noqa: F401 # pylint: disable=unused-import
from cmk.gui.valuespec import (
    ABCPageListOfMultipleGetChoice,
    AjaxDropdownChoice,
    Alternative,
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    DualListChoice,
    ElementSelection,
    FixedValue,
    Float,
    Integer,
    JSONValue,
    Labels,
    ListChoice,
    ListOf,
    ListOfMultiple,
    ListOfStrings,
    MonitoredHostname,
    Password,
    Percentage,
    RegExp,
    SingleLabel,
    TextInput,
    Transform,
    Tuple,
    Url,
    ValueSpec,
    ValueSpecHelp,
    ValueSpecText,
)
from cmk.gui.watolib.check_mk_automations import (
    get_check_information as get_check_information_automation,
)
from cmk.gui.watolib.check_mk_automations import (
    get_section_information as get_section_information_automation,
)
from cmk.gui.watolib.config_domains import ConfigDomainCore as _ConfigDomainCore
from cmk.gui.watolib.config_sync import (  # noqa: F401 # pylint: disable=unused-import
    ReplicationPath,
)
from cmk.gui.watolib.config_variable_groups import (  # noqa: F401 # pylint: disable=unused-import
    ConfigVariableGroupNotifications,
    ConfigVariableGroupSiteManagement,
    ConfigVariableGroupUserInterface,
    ConfigVariableGroupWATO,
)
from cmk.gui.watolib.host_attributes import (  # noqa: F401 # pylint: disable=unused-import
    ABCHostAttributeNagiosText,
    ABCHostAttributeNagiosValueSpec,
    ABCHostAttributeValueSpec,
    host_attribute_topic_registry,
    HostAttributeTopicAddress,
    HostAttributeTopicBasicSettings,
    HostAttributeTopicCustomAttributes,
    HostAttributeTopicDataSources,
    HostAttributeTopicHostTags,
    HostAttributeTopicManagementBoard,
    HostAttributeTopicMetaData,
    HostAttributeTopicNetworkScan,
)
from cmk.gui.watolib.password_store import PasswordStore
from cmk.gui.watolib.rulespec_groups import (  # noqa: F401 # pylint: disable=unused-import
    RulespecGroupAgentSNMP,
    RulespecGroupEnforcedServicesApplications,
    RulespecGroupEnforcedServicesEnvironment,
    RulespecGroupEnforcedServicesHardware,
    RulespecGroupEnforcedServicesNetworking,
    RulespecGroupEnforcedServicesOperatingSystem,
    RulespecGroupEnforcedServicesStorage,
    RulespecGroupEnforcedServicesVirtualization,
    RulespecGroupHostsMonitoringRulesHostChecks,
    RulespecGroupHostsMonitoringRulesNotifications,
    RulespecGroupHostsMonitoringRulesVarious,
    RulespecGroupMonitoringAgents,
    RulespecGroupMonitoringAgentsGenericOptions,
    RulespecGroupMonitoringConfiguration,
    RulespecGroupMonitoringConfigurationNotifications,
    RulespecGroupMonitoringConfigurationServiceChecks,
    RulespecGroupMonitoringConfigurationVarious,
)
from cmk.gui.watolib.rulespecs import (  # noqa: F401 # pylint: disable=unused-import
    BinaryHostRulespec,
    BinaryServiceRulespec,
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    HostRulespec,
    ManualCheckParameterRulespec,
    Rulespec,
    rulespec_group_registry,
    rulespec_registry,
    RulespecGroup,
    RulespecSubGroup,
    ServiceRulespec,
    TimeperiodValuespec,
)
from cmk.gui.watolib.users import notification_script_title


@permission_section_registry.register
class PermissionSectionWATO(PermissionSection):
    @property
    def name(self) -> str:
        return "wato"

    @property
    def title(self) -> str:
        return _("Setup")


def PluginCommandLine():
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


def monitoring_macro_help():
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


def _list_user_icons_and_actions():
    choices = []
    for key, action in active_config.user_icons_and_actions.items():
        label = key
        if "title" in action:
            label += " - " + action["title"]
        if "url" in action:
            label += " (" + action["url"][0] + ")"

        choices.append((key, label))
    return sorted(choices, key=lambda x: x[1])


def SNMPCredentials(  # pylint: disable=redefined-builtin
    title: _Optional[str] = None,
    help: _Optional[ValueSpecHelp] = None,
    only_v3: bool = False,
    default_value: _Optional[str] = "public",
    allow_none: bool = False,
    for_ec: bool = False,
) -> Alternative:
    def alternative_match(x):
        if only_v3:
            # NOTE: Indices are shifted by 1 due to a only_v3 hack below!!
            if x is None or len(x) == 2:
                return 0  # noAuthNoPriv
            if len(x) == 4:
                return 1  # authNoPriv
            if len(x) == 6:
                return 2  # authPriv
        else:
            if x is None or isinstance(x, str):
                return 0  # community only
            if len(x) == 1 or len(x) == 2:
                return 1  # noAuthNoPriv
            if len(x) == 4:
                return 2  # authNoPriv
            if len(x) == 6:
                return 3  # authPriv
        raise MKGeneralException("invalid SNMP credential format %s" % x)

    if allow_none:
        # Wrap match() function defined above
        match = lambda x: 0 if x is None else (alternative_match(x) + 1)
        elements = [_snmp_no_credentials_element()]
    else:
        match = alternative_match
        elements = []

    elements.extend(
        [
            _snmpv1_v2_credentials_element(),
            _snmpv3_no_auth_no_priv_credentials_element(),
            _snmpv3_auth_no_priv_credentials_element(),
            _snmpv3_auth_priv_credentials_element(for_ec=for_ec),
        ]
    )

    if only_v3:
        # HACK: This shifts the indices in alternative_match above!!
        # Furthermore, it doesn't work in conjunction with allow_none.
        elements.pop(0)
        title = title if title is not None else _("SNMPv3 credentials")
    else:
        title = title if title is not None else _("SNMP credentials")

    return Alternative(
        title=title,
        help=help,
        default_value=default_value,
        match=match,
        elements=elements,
    )


def _snmp_no_credentials_element() -> ValueSpec:
    return FixedValue(
        value=None,
        title=_("No explicit credentials"),
        totext="",
    )


def _snmpv1_v2_credentials_element() -> ValueSpec:
    return Password(
        title=_("SNMP community (SNMP Versions 1 and 2c)"),
        allow_empty=False,
    )


def _snmpv3_no_auth_no_priv_credentials_element() -> ValueSpec:
    return Transform(
        valuespec=Tuple(
            title=_("Credentials for SNMPv3 without authentication and privacy (noAuthNoPriv)"),
            elements=[
                FixedValue(
                    value="noAuthNoPriv",
                    title=_("Security Level"),
                    totext=_("No authentication, no privacy"),
                ),
                TextInput(title=_("Security name"), allow_empty=False),
            ],
        ),
        forth=lambda x: x if (x and len(x) == 2) else ("noAuthNoPriv", ""),
    )


def _snmpv3_auth_no_priv_credentials_element() -> ValueSpec:
    return Tuple(
        title=_("Credentials for SNMPv3 with authentication but without privacy (authNoPriv)"),
        elements=[
            FixedValue(
                value="authNoPriv",
                title=_("Security Level"),
                totext=_("authentication but no privacy"),
            ),
        ]
        + _snmpv3_auth_protocol_elements(),
    )


def _snmpv3_auth_priv_credentials_element(for_ec: bool = False) -> ValueSpec:
    priv_protocol_choices = [
        ("DES", _("CBC-DES")),
        ("AES", _("AES-128")),
    ]
    if for_ec:
        # EC uses pysnmp which supports these protocols
        # netsnmp/inline + classic do not support these protocols
        priv_protocol_choices.extend(
            [
                ("3DES-EDE", _("3DES-EDE")),
                ("AES-192", _("AES-192")),
                ("AES-256", _("AES-256")),
                ("AES-192-Blumenthal", _("AES-192-Blumenthal")),
                ("AES-256-Blumenthal", _("AES-256-Blumenthal")),
            ]
        )

    return Tuple(
        title=_("Credentials for SNMPv3 with authentication and privacy (authPriv)"),
        elements=[
            FixedValue(
                value="authPriv",
                title=_("Security Level"),
                totext=_("authentication and encryption"),
            ),
        ]
        + _snmpv3_auth_protocol_elements()
        + [
            DropdownChoice(
                choices=priv_protocol_choices,
                title=_("Privacy protocol"),
            ),
            Password(
                title=_("Privacy pass phrase"),
                minlen=8,
            ),
        ],
    )


def _snmpv3_auth_protocol_elements():
    return [
        DropdownChoice(
            choices=[
                ("md5", _("MD5 (MD5-96)")),
                ("sha", _("SHA-1 (SHA-96)")),
                ("SHA-224", _("SHA-2 (SHA-224)")),
                ("SHA-256", _("SHA-2 (SHA-256)")),
                ("SHA-384", _("SHA-2 (SHA-384)")),
                ("SHA-512", _("SHA-2 (SHA-512)")),
            ],
            title=_("Authentication protocol"),
        ),
        TextInput(
            title=_("Security name"),
        ),
        Password(
            title=_("Authentication password"),
            minlen=8,
        ),
    ]


def IPMIParameters() -> Dictionary:
    return Dictionary(
        title=_("IPMI credentials"),
        elements=[
            (
                "username",
                TextInput(
                    title=_("Username"),
                    allow_empty=False,
                ),
            ),
            (
                "password",
                Password(
                    title=_("Password"),
                    allow_empty=False,
                ),
            ),
        ],
        optional_keys=[],
    )


# NOTE: When changing this keep it in sync with cmk.utils.translations.translate_hostname()
def HostnameTranslation(**kwargs):
    help_txt = kwargs.get("help")
    title = kwargs.get("title")
    return Dictionary(
        title=title,
        help=help_txt,
        elements=[_get_drop_domain_element()] + translation_elements("host"),
    )


def _get_drop_domain_element() -> _Tuple[str, ValueSpec]:
    return (
        "drop_domain",
        FixedValue(
            value=True,
            title=_("Convert FQHN"),
            totext=_("Drop domain part (<tt>host123.foobar.de</tt> → <tt>host123</tt>)"),
        ),
    )


def ServiceDescriptionTranslation(**kwargs):
    help_txt = kwargs.get("help")
    title = kwargs.get("title")
    return Dictionary(
        title=title,
        help=help_txt,
        elements=translation_elements("service"),
    )


def translation_elements(what: str) -> List[_Tuple[str, ValueSpec]]:
    if what == "host":
        singular = "hostname"
        plural = "hostnames"

    elif what == "service":
        singular = "service description"
        plural = "service descriptions"

    else:
        raise MKGeneralException("No translations found for %s." % what)

    return [
        (
            "case",
            DropdownChoice(
                title=_("Case translation"),
                choices=[
                    (None, _("Do not convert case")),
                    ("upper", _("Convert %s to upper case") % plural),
                    ("lower", _("Convert %s to lower case") % plural),
                ],
            ),
        ),
        (
            "regex",
            Transform(
                valuespec=ListOf(
                    valuespec=Tuple(
                        orientation="horizontal",
                        elements=[
                            RegExp(
                                title=_("Regular expression"),
                                help=_("Must contain at least one subgroup <tt>(...)</tt>"),
                                mingroups=0,
                                maxgroups=9,
                                size=30,
                                allow_empty=False,
                                mode=RegExp.prefix,
                                case_sensitive=False,
                            ),
                            TextInput(
                                title=_("Replacement"),
                                help=_(
                                    "Use <tt>\\1</tt>, <tt>\\2</tt> etc. to replace matched subgroups"
                                ),
                                size=30,
                                allow_empty=False,
                            ),
                        ],
                    ),
                    title=_("Multiple regular expressions"),
                    help=_(
                        "You can add any number of expressions here which are executed succesively until the first match. "
                        "Please specify a regular expression in the first field. This expression should at "
                        "least contain one subexpression exclosed in brackets - for example <tt>vm_(.*)_prod</tt>. "
                        "In the second field you specify the translated %s and can refer to the first matched "
                        "group with <tt>\\1</tt>, the second with <tt>\\2</tt> and so on, for example <tt>\\1.example.org</tt>. "
                        ""
                    )
                    % singular,
                    add_label=_("Add expression"),
                    movable=False,
                ),
                forth=lambda x: isinstance(x, tuple) and [x] or x,
            ),
        ),
        (
            "mapping",
            ListOf(
                valuespec=Tuple(
                    orientation="horizontal",
                    elements=[
                        TextInput(
                            title=_("Original %s") % singular,
                            size=30,
                            allow_empty=False,
                        ),
                        TextInput(
                            title=_("Translated %s") % singular,
                            size=30,
                            allow_empty=False,
                        ),
                    ],
                ),
                title=_("Explicit %s mapping") % singular,
                help=_(
                    "If case conversion and regular expression do not work for all cases then you can "
                    "specify explicity pairs of origin {0} and translated {0} here. This "
                    "mapping is being applied <b>after</b> the case conversion and <b>after</b> a regular "
                    "expression conversion (if that matches)."
                ).format(singular),
                add_label=_("Add new mapping"),
                movable=False,
            ),
        ),
    ]


# TODO: Refactor this and all other childs of ElementSelection() to base on
#       DropdownChoice(). Then remove ElementSelection()
class _GroupSelection(ElementSelection):
    def __init__(self, what, choices, no_selection=None, **kwargs):
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


def ContactGroupSelection(**kwargs):
    """Select a single contact group"""
    return _GroupSelection("contact", choices=_sorted_contact_group_choices, **kwargs)


def ServiceGroupSelection(**kwargs):
    """Select a single service group"""
    return _GroupSelection("service", choices=_sorted_service_group_choices, **kwargs)


def HostGroupSelection(**kwargs):
    """Select a single host group"""
    return _GroupSelection("host", choices=_sorted_host_group_choices, **kwargs)


def ContactGroupChoice(**kwargs):
    """Select multiple contact groups"""
    return DualListChoice(choices=_sorted_contact_group_choices, **kwargs)


def ServiceGroupChoice(**kwargs):
    """Select multiple service groups"""
    return DualListChoice(choices=_sorted_service_group_choices, **kwargs)


def HostGroupChoice(**kwargs):
    """Select multiple host groups"""
    return DualListChoice(choices=_sorted_host_group_choices, **kwargs)


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


def passwordstore_choices() -> Choices:
    pw_store = PasswordStore()
    return [
        (ident, pw["title"])
        for ident, pw in pw_store.filter_usable_entries(pw_store.load_for_reading()).items()
    ]


def PasswordFromStore(  # pylint: disable=redefined-builtin
    title: _Optional[str] = None,
    help: _Optional[ValueSpecHelp] = None,
    allow_empty: bool = True,
    size: int = 25,
):  # -> CascadingDropdown
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


def IndividualOrStoredPassword(  # pylint: disable=redefined-builtin
    title: _Optional[str] = None,
    help: _Optional[ValueSpecHelp] = None,
    allow_empty: bool = True,
    size: int = 25,
):
    return Transform(
        valuespec=PasswordFromStore(
            title=title,
            help=help,
            allow_empty=allow_empty,
            size=size,
        ),
        forth=lambda v: ("password", v) if not isinstance(v, tuple) else v,
    )


_allowed_schemes = frozenset({"http", "https", "socks4", "socks4a", "socks5", "socks5h"})


def HTTPProxyReference(allowed_schemes=_allowed_schemes):
    """Use this valuespec in case you want the user to configure a HTTP proxy
    The configured value is is used for preparing requests to work in a proxied environment."""

    def _global_proxy_choices():
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
            kwargs["item_spec"] = lambda: itemspec

        base_class = (
            CheckParameterRulespecWithItem
            if itemspec is not None
            else CheckParameterRulespecWithoutItem
        )

        rulespec_registry.register(base_class(**kwargs))

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
    def main_group(self):
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self):
        return "networking"

    @property
    def title(self) -> str:
        return _("Networking")


@rulespec_group_registry.register
class RulespecGroupCheckParametersStorage(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self):
        return "storage"

    @property
    def title(self) -> str:
        return _("Storage, Filesystems and Files")


@rulespec_group_registry.register
class RulespecGroupCheckParametersOperatingSystem(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self):
        return "os"

    @property
    def title(self) -> str:
        return _("Operating System Resources")


@rulespec_group_registry.register
class RulespecGroupCheckParametersPrinters(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self):
        return "printers"

    @property
    def title(self) -> str:
        return _("Printers")


@rulespec_group_registry.register
class RulespecGroupCheckParametersEnvironment(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self):
        return "environment"

    @property
    def title(self) -> str:
        return _("Temperature, Humidity, Electrical Parameters, etc.")


@rulespec_group_registry.register
class RulespecGroupCheckParametersApplications(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self):
        return "applications"

    @property
    def title(self) -> str:
        return _("Applications, Processes & Services")


@rulespec_group_registry.register
class RulespecGroupCheckParametersVirtualization(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self):
        return "virtualization"

    @property
    def title(self) -> str:
        return _("Virtualization")


@rulespec_group_registry.register
class RulespecGroupCheckParametersHardware(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self):
        return "hardware"

    @property
    def title(self) -> str:
        return _("Hardware, BIOS")


@rulespec_group_registry.register
class RulespecGroupCheckParametersDiscovery(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupDiscoveryCheckParameters

    @property
    def sub_group_name(self):
        return "discovery"

    @property
    def title(self) -> str:
        return _("Discovery of individual services")


# The following function looks like a value spec and in fact
# can be used like one (but take no parameters)
def PredictiveLevels(
    default_difference: _Tuple[float, float] = (2.0, 4.0), unit: str = ""
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
                                        unit=_("% above predicted value"),
                                        default_value=10,
                                    ),
                                    Percentage(
                                        title=_("Critical at"),
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
                                        unit=_("% below predicted value"),
                                        default_value=10,
                                    ),
                                    Percentage(
                                        title=_("Critical at"),
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
    help: _Optional[str] = None,  # pylint: disable=redefined-builtin
    default_levels: _Tuple[float, float] = (0.0, 0.0),
    default_difference: _Tuple[float, float] = (0.0, 0.0),
    default_value: _Optional[_Tuple[float, float]] = None,
    title: _Optional[str] = None,
    unit: str = "",
) -> Alternative:
    def match_levels_alternative(v: Union[Dict[Any, Any], _Tuple[Any, Any]]) -> int:
        if isinstance(v, dict):
            return 2
        if isinstance(v, tuple) and v != (None, None):
            return 1
        return 0

    if not isinstance(unit, str):
        raise ValueError(f"illegal unit for Levels: {unit}, expected a string")

    if default_value is None:
        default_value = default_levels

    elements = [
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
        forth=lambda list_: {
            k: v
            for k, v in (
                ("host", [name for name in list_ if not name.startswith("mgmt_")]),
                ("mgmt", [name[5:] for name in list_ if name.startswith("mgmt_")]),
            )
            if v or k == "host"
        },
        back=lambda dict_: dict_["host"] + [f"mgmt_{n}" for n in dict_.get("mgmt", ())],
    )


class _CheckTypeHostSelection(DualListChoice):
    def __init__(self, **kwargs):
        super().__init__(rows=25, **kwargs)

    def get_elements(self):
        checks = get_check_information()
        return [
            (str(cn), (str(cn) + " - " + c["title"])[:60])
            for (cn, c) in checks.items()
            # filter out plugins implemented *explicitly* for management boards
            if not cn.is_management_name()
        ]


class _CheckTypeMgmtSelection(DualListChoice):
    def __init__(self, **kwargs):
        super().__init__(rows=25, **kwargs)

    def get_elements(self):
        checks = get_check_information()
        return [
            (str(cn.create_basic_name()), (str(cn) + " - " + c["title"])[:60])
            for (cn, c) in checks.items()
        ]


class ConfigHostname(AjaxDropdownChoice):
    """Hostname input with dropdown completion

    Renders an input field for entering a host name while providing an auto completion dropdown field.
    Fetching the choices from the current WATO config"""

    ident = "config_hostname"


class ABCEventsMode(WatoMode, abc.ABC):
    @classmethod
    @abc.abstractmethod
    def _rule_match_conditions(cls):
        raise NotImplementedError()

    # flavour = "notify" or "alert"
    @classmethod
    def _event_rule_match_conditions(cls, flavour):
        if flavour == "notify":
            add_choices = [
                ("f", _("Start or end of flapping state")),
                ("s", _("Start or end of a scheduled downtime")),
                ("x", _("Acknowledgement of problem")),
                ("as", _("Alert handler execution, successful")),
                ("af", _("Alert handler execution, failed")),
            ]
            add_default = ["f", "s", "x", "as", "af"]
        else:
            add_choices = []
            add_default = []

        return [
            (
                "match_host_event",
                ListChoice(
                    title=_("Match host event type"),
                    help=(
                        _(
                            "Select the host event types and transitions this rule should handle.<br>"
                            "Note: If you activate this option and do <b>not</b> also specify service event "
                            "types then this rule will never hold for service notifications!<br>"
                            'Note: You can only match on event types <a href="%s">created by the core</a>.'
                        )
                        % "wato.py?mode=edit_ruleset&varname=extra_host_conf%3Anotification_options"
                    ),
                    choices=[
                        ("rd", _("UP") + " ➤ " + _("DOWN")),
                        ("ru", _("UP") + " ➤ " + _("UNREACHABLE")),
                        ("dr", _("DOWN") + " ➤ " + _("UP")),
                        ("du", _("DOWN") + " ➤ " + _("UNREACHABLE")),
                        ("ud", _("UNREACHABLE") + " ➤ " + _("DOWN")),
                        ("ur", _("UNREACHABLE") + " ➤ " + _("UP")),
                        ("?r", _("any") + " ➤ " + _("UP")),
                        ("?d", _("any") + " ➤ " + _("DOWN")),
                        ("?u", _("any") + " ➤ " + _("UNREACHABLE")),
                    ]
                    + add_choices,
                    default_value=[
                        "rd",
                        "dr",
                    ]
                    + add_default,
                ),
            ),
            (
                "match_service_event",
                ListChoice(
                    title=_("Match service event type"),
                    help=(
                        _(
                            "Select the service event types and transitions this rule should handle.<br>"
                            "Note: If you activate this option and do <b>not</b> also specify host event "
                            "types then this rule will never hold for host notifications!<br>"
                            'Note: You can only match on event types <a href="%s">created by the core</a>.'
                        )
                        % "wato.py?mode=edit_ruleset&varname=extra_service_conf%3Anotification_options"
                    ),
                    choices=[
                        ("rw", _("OK") + " ➤ " + _("WARN")),
                        ("rr", _("OK") + " ➤ " + _("OK")),
                        ("rc", _("OK") + " ➤ " + _("CRIT")),
                        ("ru", _("OK") + " ➤ " + _("UNKNOWN")),
                        ("wr", _("WARN") + " ➤ " + _("OK")),
                        ("wc", _("WARN") + " ➤ " + _("CRIT")),
                        ("wu", _("WARN") + " ➤ " + _("UNKNOWN")),
                        ("cr", _("CRIT") + " ➤ " + _("OK")),
                        ("cw", _("CRIT") + " ➤ " + _("WARN")),
                        ("cu", _("CRIT") + " ➤ " + _("UNKNOWN")),
                        ("ur", _("UNKNOWN") + " ➤ " + _("OK")),
                        ("uw", _("UNKNOWN") + " ➤ " + _("WARN")),
                        ("uc", _("UNKNOWN") + " ➤ " + _("CRIT")),
                        ("?r", _("any") + " ➤ " + _("OK")),
                        ("?w", _("any") + " ➤ " + _("WARN")),
                        ("?c", _("any") + " ➤ " + _("CRIT")),
                        ("?u", _("any") + " ➤ " + _("UNKNOWN")),
                    ]
                    + add_choices,
                    default_value=[
                        "rw",
                        "rc",
                        "ru",
                        "wc",
                        "wu",
                        "uc",
                    ]
                    + add_default,
                ),
            ),
        ]

    @classmethod
    def _generic_rule_match_conditions(cls):
        return _simple_host_rule_match_conditions() + [
            (
                "match_servicelabels",
                Labels(
                    world=Labels.World.CORE,
                    title=_("Match service labels"),
                    help=_(
                        "Use this condition to select hosts based on the configured service labels."
                    ),
                ),
            ),
            (
                "match_servicegroups",
                ServiceGroupChoice(
                    title=_("Match service groups"),
                    help=_(
                        "The service must be in one of the selected service groups. For host events this condition "
                        "never matches as soon as at least one group is selected."
                    ),
                    allow_empty=False,
                ),
            ),
            (
                "match_exclude_servicegroups",
                ServiceGroupChoice(
                    title=_("Exclude service groups"),
                    help=_(
                        "The service must not be in one of the selected service groups. For host events this condition "
                        "is simply ignored."
                    ),
                    allow_empty=False,
                ),
            ),
            (
                "match_servicegroups_regex",
                Tuple(
                    title=_("Match service groups (regex)"),
                    elements=[
                        DropdownChoice(
                            choices=[
                                ("match_id", _("Match the internal identifier")),
                                ("match_alias", _("Match the alias")),
                            ],
                            default_value="match_id",
                        ),
                        ListOfStrings(
                            help=_(
                                "The service group alias must match one of the following regular expressions."
                                " For host events this condition never matches as soon as at least one group is selected."
                            ),
                            valuespec=RegExp(
                                size=32,
                                mode=RegExp.infix,
                            ),
                            orientation="horizontal",
                        ),
                    ],
                ),
            ),
            (
                "match_exclude_servicegroups_regex",
                Tuple(
                    title=_("Exclude service groups (regex)"),
                    elements=[
                        DropdownChoice(
                            choices=[
                                ("match_id", _("Match the internal identifier")),
                                ("match_alias", _("Match the alias")),
                            ],
                            default_value="match_id",
                        ),
                        ListOfStrings(
                            help=_(
                                "The service group alias must not match one of the following regular expressions. "
                                "For host events this condition is simply ignored."
                            ),
                            valuespec=RegExp(
                                size=32,
                                mode=RegExp.infix,
                            ),
                            orientation="horizontal",
                        ),
                    ],
                ),
            ),
            (
                "match_services",
                ListOfStrings(
                    title=_("Match services"),
                    help=_(
                        "Specify a list of regular expressions that must match the <b>beginning</b> of the "
                        "service name in order for the rule to match. Note: Host notifications never match this "
                        "rule if this option is being used."
                    ),
                    valuespec=RegExp(
                        size=32,
                        mode=RegExp.prefix,
                    ),
                    orientation="horizontal",
                    allow_empty=False,
                    empty_text=_(
                        "Please specify at least one service regex. Disable the option if you want to allow all services."
                    ),
                ),
            ),
            (
                "match_exclude_services",
                ListOfStrings(
                    title=_("Exclude services"),
                    valuespec=RegExp(
                        size=32,
                        mode=RegExp.prefix,
                    ),
                    orientation="horizontal",
                ),
            ),
            (
                "match_checktype",
                valuespec_check_plugin_selection(
                    title=_("Match check types"),
                    help_=_(
                        "Only apply the rule if the notification originates from certain types of check plugins. "
                        "Note: Host notifications never match this rule if this option is being used."
                    ),
                ),
            ),
            (
                "match_plugin_output",
                RegExp(
                    title=_("Match check plugin output"),
                    help=_(
                        "This text is a regular expression that is being searched in the output "
                        "of the check plugins that produced the alert. It is not a prefix but an infix match."
                    ),
                    mode=RegExp.prefix,
                ),
            ),
            (
                "match_contacts",
                ListOf(
                    valuespec=userdb.UserSelection(only_contacts=True),
                    title=_("Match contacts"),
                    help=_("The host/service must have one of the selected contacts."),
                    movable=False,
                    allow_empty=False,
                    add_label=_("Add contact"),
                ),
            ),
            (
                "match_contactgroups",
                ContactGroupChoice(
                    title=_("Match contact groups"),
                    help=_(
                        "The host/service must be in one of the selected contact groups. This only works with Check_MK Micro Core. "
                        "If you don't use the CMC that filter will not apply"
                    ),
                    allow_empty=False,
                ),
            ),
            (
                "match_sl",
                Tuple(
                    title=_("Match service level"),
                    help=_(
                        "Host or service must be in the following service level to get notification"
                    ),
                    orientation="horizontal",
                    show_titles=False,
                    elements=[
                        DropdownChoice(
                            label=_("from:"),
                            choices=cmk.gui.mkeventd.service_levels,
                            prefix_values=True,
                        ),
                        DropdownChoice(
                            label=_(" to:"),
                            choices=cmk.gui.mkeventd.service_levels,
                            prefix_values=True,
                        ),
                    ],
                ),
            ),
            (
                "match_timeperiod",
                _timeperiods.TimeperiodSelection(
                    title=_("Match only during timeperiod"),
                    help=_(
                        "Match this rule only during times where the selected timeperiod from the monitoring "
                        "system is active."
                    ),
                ),
            ),
        ]

    @abc.abstractmethod
    def _add_change(self, log_what, log_text):
        raise NotImplementedError()

    def _generic_rule_list_actions(self, rules, what, what_title, save_rules) -> None:
        if request.has_var("_delete"):
            nr = request.get_integer_input_mandatory("_delete")
            self._add_change(what + "-delete-rule", _("Deleted %s %d") % (what_title, nr))
            del rules[nr]
            save_rules(rules)

        elif request.has_var("_move"):
            if transactions.check_transaction():
                from_pos = request.get_integer_input_mandatory("_move")
                to_pos = request.get_integer_input_mandatory("_index")
                rule = rules[from_pos]
                del rules[from_pos]  # make to_pos now match!
                rules[to_pos:to_pos] = [rule]
                save_rules(rules)
                self._add_change(
                    what + "-move-rule", _("Changed position of %s %d") % (what_title, from_pos)
                )


def sort_sites(sites: SiteConfigurations) -> List[_Tuple[SiteId, SiteConfiguration]]:
    """Sort given sites argument by local, followed by remote sites"""
    return sorted(
        sites.items(),
        key=lambda sid_s: (sid_s[1].get("replication") or "", sid_s[1].get("alias", ""), sid_s[0]),
    )


# Show HTML form for editing attributes.
#
# new: Boolean flag if this is a creation step or editing
# for_what can be:
#   "host"        -> normal host edit dialog
#   "cluster"     -> normal host edit dialog
#   "folder"      -> properties of folder or file
#   "host_search" -> host search dialog
#   "bulk"        -> bulk change
# parent: The parent folder of the objects to configure
# myself: For mode "folder" the folder itself or None, if we edit a new folder
#         This is needed for handling mandatory attributes.
#
# This is the counterpart of "collect_attributes". Another place which
# is related to these HTTP variables and so on is SearchFolder.
#
# TODO: Wow, this function REALLY has to be cleaned up
def configure_attributes(
    new,
    hosts,
    for_what,
    parent,
    myself=None,
    without_attributes=None,
    varprefix="",
    basic_attributes=None,
):
    if without_attributes is None:
        without_attributes = []
    if basic_attributes is None:
        basic_attributes = []

    # Collect dependency mapping for attributes (attributes that are only
    # visible, if certain host tags are set).
    dependency_mapping_tags = {}
    dependency_mapping_roles = {}
    inherited_tags = {}

    volatile_topics = []
    hide_attributes = []
    show_more_mode: bool = False

    show_more_mode = user.show_mode != "default_show_less"

    for topic_id, topic_title in _host_attributes.get_sorted_host_attribute_topics(for_what, new):
        topic_is_volatile = True  # assume topic is sometimes hidden due to dependencies
        topic_attributes = _host_attributes.get_sorted_host_attributes_by_topic(topic_id)

        forms.header(
            topic_title,
            isopen=topic_id in ["basic", "address", "monitoring_agents"],
            table_id=topic_id,
            show_more_toggle=any(attribute.is_show_more() for attribute in topic_attributes),
            show_more_mode=show_more_mode,
        )

        if topic_id == "basic":
            for attr_varprefix, vs, default_value in basic_attributes:
                forms.section(_u(vs.title()), is_required=not vs.allow_empty())
                vs.render_input(attr_varprefix, default_value)

        for attr in topic_attributes:
            attrname = attr.name()
            if attrname in without_attributes:
                continue  # e.g. needed to skip ipaddress in CSV-Import

            # Determine visibility information if this attribute is not always hidden
            if attr.is_visible(for_what, new):
                depends_on_tags = attr.depends_on_tags()
                depends_on_roles = attr.depends_on_roles()
                # Add host tag dependencies, but only in host mode. In other
                # modes we always need to show all attributes.
                if for_what in ["host", "cluster"] and depends_on_tags:
                    dependency_mapping_tags[attrname] = depends_on_tags

                if depends_on_roles:
                    dependency_mapping_roles[attrname] = depends_on_roles

                if for_what not in ["host", "cluster"]:
                    topic_is_volatile = False

                elif not depends_on_tags and not depends_on_roles:
                    # One attribute is always shown -> topic is always visible
                    topic_is_volatile = False
            else:
                hide_attributes.append(attr.name())

            # "bulk": determine, if this attribute has the same setting for all hosts.
            values = []
            num_have_locked_it = 0
            num_haveit = 0
            for host in hosts.values():
                if not host:
                    continue

                locked_by = host.attribute("locked_by")
                locked_attributes = host.attribute("locked_attributes")
                if locked_by and locked_attributes and attrname in locked_attributes:
                    num_have_locked_it += 1

                if host.has_explicit_attribute(attrname):
                    num_haveit += 1
                    if host.attribute(attrname) not in values:
                        values.append(host.attribute(attrname))

            # The value of this attribute is unique amongst all hosts if
            # either no host has a value for this attribute, or all have
            # one and have the same value
            unique = num_haveit == 0 or (len(values) == 1 and num_haveit == len(hosts))

            if for_what in ["host", "cluster", "folder"]:
                if hosts:
                    host = list(hosts.values())[0]
                else:
                    host = None

            # Collect information about attribute values inherited from folder.
            # This information is just needed for informational display to the user.
            # This does not apply in "host_search" mode.
            inherited_from: _Optional[HTML] = None
            inherited_value = None
            has_inherited = False
            container = None

            if attr.show_inherited_value():
                if for_what in ["host", "cluster"]:
                    url = _hosts_and_folders.Folder.current().edit_url()

                container = parent  # container is of type Folder
                while container:
                    if attrname in container.attributes():
                        url = container.edit_url()
                        inherited_from = escape_to_html(_("Inherited from ")) + HTMLWriter.render_a(
                            container.title(), href=url
                        )

                        inherited_value = container.attributes()[attrname]
                        has_inherited = True
                        if attr.is_tag_attribute:
                            inherited_tags["attr_%s" % attrname] = inherited_value
                        break

                    container = container.parent()

            if not container:  # We are the root folder - we inherit the default values
                inherited_from = escape_to_html(_("Default value"))
                inherited_value = attr.default_value()
                # Also add the default values to the inherited values dict
                if attr.is_tag_attribute:
                    inherited_tags["attr_%s" % attrname] = inherited_value

            # Checkbox for activating this attribute

            # Determine current state of visibility: If the form has already been submitted (i.e. search
            # or input error), then we take the previous state of the box. In search mode we make those
            # boxes active that have an empty string as default value (simple text boxed). In bulk
            # mode we make those attributes active that have an explicitely set value over all hosts.
            # In host and folder mode we make those attributes active that are currently set.

            # Also determine, if the attribute can be switched off at all. Problematic here are
            # mandatory attributes. We must make sure, that at least one folder/file/host in the
            # chain defines an explicit value for that attribute. If we show a host and no folder/file
            # inherits an attribute to that host, the checkbox will be always active and locked.
            # The same is the case if we show a file/folder and at least one host below this
            # has not set that attribute. In case of bulk edit we never lock: During bulk edit no
            # attribute ca be removed anyway.

            checkbox_name = for_what + "_change_%s" % attrname
            cb = html.get_checkbox(checkbox_name)
            force_entry = False
            disabled = False

            # first handle mandatory cases
            if (
                for_what == "folder"
                and attr.is_mandatory()
                and myself
                and some_host_hasnt_set(myself, attrname)
                and not has_inherited
            ):
                force_entry = True
                active = True
            elif for_what in ["host", "cluster"] and attr.is_mandatory() and not has_inherited:
                force_entry = True
                active = True
            elif cb is not None:
                active = cb  # get previous state of checkbox
            elif for_what == "bulk":
                active = unique and len(values) > 0
            elif for_what == "folder" and myself:
                active = myself.has_explicit_attribute(attrname)
            elif for_what in ["host", "cluster"] and host:  # "host"
                active = host.has_explicit_attribute(attrname)
            else:
                active = False

            is_editable = attr.editable() and attr.may_edit() and num_have_locked_it == 0
            if for_what == "host_search":
                is_editable = True

            if not is_editable:
                # Bug in pylint 1.9.2 https://github.com/PyCQA/pylint/issues/1984, already fixed in master.
                if active:  # pylint: disable=simplifiable-if-statement
                    force_entry = True
                else:
                    disabled = True

            if (for_what in ["host", "cluster"] and parent.locked_hosts()) or (
                for_what == "folder" and myself and myself.locked()
            ):
                checkbox_code = None
            elif force_entry:
                checkbox_code = html.render_checkbox(
                    "ignored_" + checkbox_name, disabled="disabled"
                )
                checkbox_code += html.render_hidden_field(checkbox_name, "on")
            else:
                onclick = (
                    "cmk.wato.fix_visibility(); cmk.wato.toggle_attribute(this, '%s');" % attrname
                )
                checkbox_kwargs = {"disabled": "disabled"} if disabled else {}
                checkbox_code = html.render_checkbox(
                    checkbox_name, active, onclick=onclick, **checkbox_kwargs
                )

            forms.section(
                _u(attr.title()),
                checkbox=checkbox_code,
                section_id="attr_" + attrname,
                is_show_more=attr.is_show_more(),
                is_changed=active,
            )
            html.help(attr.help())

            if len(values) == 1:
                defvalue = values[0]
            elif attr.is_checkbox_tag:
                defvalue = True
            else:
                defvalue = attr.default_value()

            if not new and not is_editable:
                # In edit mode only display non editable values, don't show the
                # input fields
                html.open_div(id_="attr_hidden_%s" % attrname, style="display:none;")
                attr.render_input(varprefix, defvalue)
                html.close_div()

                html.open_div(id_="attr_visible_%s" % attrname, class_=["inherited"])

            else:
                # Now comes the input fields and the inherited / default values
                # as two DIV elements, one of which is visible at one time.

                # DIV with the input elements
                html.open_div(
                    id_="attr_entry_%s" % attrname, style="display: none;" if not active else None
                )
                attr.render_input(varprefix, defvalue)
                html.close_div()

                html.open_div(
                    class_="inherited",
                    id_="attr_default_%s" % attrname,
                    style="display: none;" if active else None,
                )

            #
            # DIV with actual / inherited / default value
            #

            # in bulk mode we show inheritance only if *all* hosts inherit
            explanation: HTML = HTML("")
            if for_what == "bulk":
                if num_haveit == 0:
                    assert inherited_from is not None
                    explanation = HTML(" (") + inherited_from + HTML(")")
                    value = inherited_value
                elif not unique:
                    explanation = escape_to_html(
                        _("This value differs between the selected hosts.")
                    )
                else:
                    value = values[0]

            elif for_what in ["host", "cluster", "folder"]:
                if not new and not is_editable and active:
                    value = values[0]
                else:
                    if inherited_from is not None:
                        explanation = " (" + inherited_from + ")"
                    value = inherited_value

            if for_what != "host_search" and not (for_what == "bulk" and not unique):
                _tdclass, content = attr.paint(value, "")
                if not content:
                    content = _("empty")

                if isinstance(attr, ABCHostAttributeValueSpec):
                    html.open_b()
                    html.write_text(content)
                    html.close_b()
                elif isinstance(attr, str):
                    html.b(_u(cast(str, content)))
                else:
                    html.b(content)

            html.write_text(explanation)
            html.close_div()

        if topic_is_volatile:
            volatile_topics.append(topic_id)

    forms.end()

    dialog_properties = {
        "inherited_tags": inherited_tags,
        "check_attributes": list(
            set(dependency_mapping_tags.keys())
            | set(dependency_mapping_roles.keys())
            | set(hide_attributes)
        ),
        "aux_tags_by_tag": active_config.tags.get_aux_tags_by_tag(),
        "depends_on_tags": dependency_mapping_tags,
        "depends_on_roles": dependency_mapping_roles,
        "volatile_topics": volatile_topics,
        "user_roles": user.role_ids,
        "hide_attributes": hide_attributes,
    }
    html.javascript(
        "cmk.wato.prepare_edit_dialog(%s);"
        "cmk.wato.fix_visibility();" % json.dumps(dialog_properties)
    )


# Check if at least one host in a folder (or its subfolders)
# has not set a certain attribute. This is needed for the validation
# of mandatory attributes.
def some_host_hasnt_set(folder, attrname):
    # Check subfolders
    for subfolder in folder.subfolders():
        # If the attribute is not set in the subfolder, we need
        # to check all hosts and that folder.
        if attrname not in subfolder.attributes() and some_host_hasnt_set(subfolder, attrname):
            return True

    # Check hosts in this folder
    for host in folder.hosts().values():
        if not host.has_explicit_attribute(attrname):
            return True

    return False


class SiteBackupJobs(backup.Jobs):
    def __init__(self) -> None:
        super().__init__(backup.site_config_path())

    def _apply_cron_config(self):
        completed_process = subprocess.run(
            ["omd", "restart", "crontab"],
            close_fds=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            stdin=subprocess.DEVNULL,
            check=False,
        )
        if completed_process.returncode:
            raise MKGeneralException(
                _("Failed to apply the cronjob config: %s") % completed_process.stdout
            )


# TODO: Kept for compatibility with pre-1.6 WATO plugins
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
    cmk.utils.plugin_registry.Registry[Type[NotificationParameter]]
):
    def plugin_name(self, instance):
        return instance().ident

    def registration_hook(self, instance):
        plugin = instance()

        script_title = notification_script_title(plugin.ident)

        valuespec = plugin.spec
        # TODO: Cleanup this hack
        valuespec._title = _("Call with the following parameters:")

        _rulespecs.register_rule(
            rulespec_group_registry["monconf/notifications"],
            "notification_parameters:" + plugin.ident,
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


class DictHostTagCondition(Transform):
    def __init__(self, title, help_txt):
        super().__init__(
            valuespec=ListOfMultiple(
                title=title,
                help=help_txt,
                choices=self._get_cached_tag_group_choices(),
                choice_page_name="ajax_dict_host_tag_condition_get_choice",
                add_label=_("Add tag condition"),
                del_label=_("Remove tag condition"),
            ),
            forth=self._to_valuespec,
            back=self._from_valuespec,
        )

    @request_memoize()
    def _get_cached_tag_group_choices(self):
        # In case one has configured a lot of tag groups / id recomputing this for
        # every DictHostTagCondition instance takes a lot of time
        return self._get_tag_group_choices()

    def _get_tag_group_choices(self):
        choices = []
        all_topics = active_config.tags.get_topic_choices()
        tag_groups_by_topic = dict(active_config.tags.get_tag_groups_by_topic())
        aux_tags_by_topic = dict(active_config.tags.get_aux_tags_by_topic())
        for topic_id, _topic_title in all_topics:
            for tag_group in tag_groups_by_topic.get(topic_id, []):
                choices.append(self._get_tag_group_choice(tag_group))

            for aux_tag in aux_tags_by_topic.get(topic_id, []):
                choices.append(self._get_aux_tag_choice(aux_tag))

        return choices

    def _to_valuespec(self, host_tag_conditions):
        valuespec_value = {}
        for tag_group_id, tag_condition in host_tag_conditions.items():
            if isinstance(tag_condition, dict) and "$or" in tag_condition:
                value = self._ored_tags_to_valuespec(tag_condition["$or"])
            elif isinstance(tag_condition, dict) and "$nor" in tag_condition:
                value = self._nored_tags_to_valuespec(tag_condition["$nor"])
            else:
                value = self._single_tag_to_valuespec(tag_condition)

            valuespec_value[tag_group_id] = value

        return valuespec_value

    def _ored_tags_to_valuespec(self, tag_conditions):
        return ("or", tag_conditions)

    def _nored_tags_to_valuespec(self, tag_conditions):
        return ("nor", tag_conditions)

    def _single_tag_to_valuespec(self, tag_condition):
        if isinstance(tag_condition, dict):
            if "$ne" in tag_condition:
                return ("is_not", tag_condition["$ne"])
            raise NotImplementedError()
        return ("is", tag_condition)

    def _from_valuespec(self, valuespec_value):
        tag_conditions = {}
        for tag_group_id, (operator, operand) in valuespec_value.items():
            if operator in ["is", "is_not"]:
                tag_group_value = self._single_tag_from_valuespec(operator, operand)
            elif operator in ["or", "nor"]:
                tag_group_value = {
                    "$%s" % operator: operand,
                }
            else:
                raise NotImplementedError()

            tag_conditions[tag_group_id] = tag_group_value
        return tag_conditions

    def _single_tag_from_valuespec(self, operator, tag_id):
        if operator == "is":
            return tag_id
        if operator == "is_not":
            return {"$ne": tag_id}
        raise NotImplementedError()

    def _get_tag_group_choice(self, tag_group):
        tag_choices = tag_group.get_tag_choices()

        if len(tag_choices) == 1:
            return self._single_tag_choice(
                tag_group_id=tag_group.id,
                choice_title=tag_group.choice_title,
                tag_id=tag_group.tags[0].id,
                title=tag_group.tags[0].title,
            )

        tag_id_choice = ListOf(
            valuespec=DropdownChoice(
                choices=tag_choices,
            ),
            style=ListOf.Style.FLOATING,
            add_label=_("Add tag"),
            del_label=_("Remove tag"),
            magic="@@#!#@@",
            movable=False,
            validate=lambda value, varprefix: self._validate_tag_list(
                value, varprefix, tag_choices
            ),
        )

        return (
            tag_group.id,
            CascadingDropdown(
                label=tag_group.choice_title + " ",
                title=tag_group.choice_title,
                choices=[
                    ("is", _("is"), DropdownChoice(choices=tag_choices)),
                    ("is_not", _("is not"), DropdownChoice(choices=tag_choices)),
                    ("or", _("one of"), tag_id_choice),
                    ("nor", _("none of"), tag_id_choice),
                ],
                orientation="horizontal",
                default_value=("is", tag_choices[0][0]),
            ),
        )

    def _validate_tag_list(self, value, varprefix, tag_choices):
        seen = set()
        for tag_id in value:
            if tag_id in seen:
                raise MKUserError(
                    varprefix,
                    _("The tag '%s' is selected multiple times. A tag may be selected only once.")
                    % dict(tag_choices)[tag_id],
                )
            seen.add(tag_id)

    def _get_aux_tag_choice(self, aux_tag):
        return self._single_tag_choice(
            tag_group_id=aux_tag.id,
            choice_title=aux_tag.choice_title,
            tag_id=aux_tag.id,
            title=aux_tag.title,
        )

    def _single_tag_choice(self, tag_group_id, choice_title, tag_id, title):
        return (
            tag_group_id,
            Tuple(
                title=choice_title,
                elements=[
                    self._is_or_is_not(
                        label=choice_title + " ",
                    ),
                    FixedValue(
                        value=tag_id,
                        title=_u(title),
                        totext=_u(title),
                    ),
                ],
                show_titles=False,
                orientation="horizontal",
            ),
        )

    def _tag_choice(self, tag_group):
        return Tuple(
            title=_u(tag_group.choice_title),
            elements=[
                self._is_or_is_not(),
                DropdownChoice(choices=tag_group.get_tag_choices()),
            ],
            show_titles=False,
            orientation="horizontal",
        )

    def _is_or_is_not(self, **kwargs):
        return DropdownChoice(
            choices=[
                ("is", _("is")),
                ("is_not", _("is not")),
            ],
            **kwargs,
        )


class HostTagCondition(ValueSpec[Sequence[str]]):
    """ValueSpec for editing a tag-condition"""

    def render_input(self, varprefix: str, value: Sequence[str]) -> None:
        self._render_condition_editor(varprefix, value)

    def from_html_vars(self, varprefix: str) -> Sequence[str]:
        return self._get_tag_conditions(varprefix)

    def _get_tag_conditions(self, varprefix: str) -> Sequence[str]:
        """Retrieve current tag condition settings from HTML variables"""
        if varprefix:
            varprefix += "_"

        # Main tags
        tag_list = []
        for tag_group in active_config.tags.tag_groups:
            if tag_group.is_checkbox_tag_group:
                tagvalue = tag_group.default_value
            else:
                tagvalue = request.var(varprefix + "tagvalue_" + tag_group.id)
            assert tagvalue is not None

            mode = request.var(varprefix + "tag_" + tag_group.id)
            if mode == "is":
                tag_list.append(tagvalue)
            elif mode == "isnot":
                tag_list.append("!" + tagvalue)

        # Auxiliary tags
        for aux_tag in active_config.tags.aux_tag_list.get_tags():
            mode = request.var(varprefix + "auxtag_" + aux_tag.id)
            if mode == "is":
                tag_list.append(aux_tag.id)
            elif mode == "isnot":
                tag_list.append("!" + aux_tag.id)

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
            container: ContextManager[bool] = (
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
        self, choices: Sequence[tuple[_Optional[str], str]], tag_specs: Sequence[str]
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
        onchange = "cmk.valuespecs.toggle_tag_dropdown(this, '%stag_sel_%s');" % (varprefix, id_)
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
            id_="%stag_sel_%s" % (varprefix, id_),
            style="display: none;" if not div_is_open else None,
        )

    def value_to_json(self, value: Sequence[str]) -> JSONValue:
        raise NotImplementedError()  # FIXME! Violates LSP!

    def value_from_json(self, json_value: JSONValue) -> Sequence[str]:
        raise NotImplementedError()  # FIXME! Violates LSP!


class LabelCondition(Transform):
    def __init__(self, title, help_txt):
        super().__init__(
            valuespec=ListOf(
                valuespec=Tuple(
                    orientation="horizontal",
                    elements=[
                        DropdownChoice(
                            choices=[
                                ("is", _("has")),
                                ("is_not", _("has not")),
                            ],
                        ),
                        SingleLabel(
                            world=Labels.World.CONFIG,
                        ),
                    ],
                    show_titles=False,
                ),
                add_label=_("Add label condition"),
                del_label=_("Remove label condition"),
                style=ListOf.Style.FLOATING,
                movable=False,
            ),
            forth=self._to_valuespec,
            back=self._from_valuespec,
            title=title,
            help=help_txt,
        )

    def _to_valuespec(self, label_conditions):
        valuespec_value = []
        for label_id, label_value in label_conditions.items():
            valuespec_value.append(self._single_label_to_valuespec(label_id, label_value))
        return valuespec_value

    def _single_label_to_valuespec(self, label_id, label_value):
        if isinstance(label_value, dict):
            if "$ne" in label_value:
                return ("is_not", {label_id: label_value["$ne"]})
            raise NotImplementedError()
        return ("is", {label_id: label_value})

    def _from_valuespec(self, valuespec_value):
        label_conditions = {}
        for operator, label in valuespec_value:
            if label:
                label_id, label_value = list(label.items())[0]
                label_conditions[label_id] = self._single_label_from_valuespec(
                    operator, label_value
                )
        return label_conditions

    def _single_label_from_valuespec(self, operator, label_value):
        if operator == "is":
            return label_value
        if operator == "is_not":
            return {"$ne": label_value}
        raise NotImplementedError()


@page_registry.register_page("ajax_dict_host_tag_condition_get_choice")
class PageAjaxDictHostTagConditionGetChoice(ABCPageListOfMultipleGetChoice):
    def _get_choices(self, api_request):
        condition = DictHostTagCondition("Dummy title", "Dummy help")
        return condition._get_tag_group_choices()


def transform_simple_to_multi_host_rule_match_conditions(value):
    if value and "match_folder" in value:
        value["match_folders"] = [value.pop("match_folder")]
    return value


def _simple_host_rule_match_conditions():
    return [
        _site_rule_match_condition(),
        _single_folder_rule_match_condition(),
    ] + _common_host_rule_match_conditions()


def multifolder_host_rule_match_conditions():
    return [
        _site_rule_match_condition(),
        _multi_folder_rule_match_condition(),
    ] + _common_host_rule_match_conditions()


def _site_rule_match_condition():
    return (
        "match_site",
        DualListChoice(
            title=_("Match sites"),
            help=_("This condition makes the rule match only hosts of the selected sites."),
            choices=get_activation_site_choices,
        ),
    )


def _multi_folder_rule_match_condition():
    return (
        "match_folders",
        ListOf(
            valuespec=FullPathFolderChoice(
                title=_("Folder"),
                help=_(
                    "This condition makes the rule match only hosts that are managed "
                    "via WATO and that are contained in this folder - either directly "
                    "or in one of its subfolders."
                ),
            ),
            add_label=_("Add additional folder"),
            title=_("Match folders"),
            movable=False,
        ),
    )


def _common_host_rule_match_conditions():
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
                valuespec=MonitoredHostname(),
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
                valuespec=MonitoredHostname(),
                title=_("Exclude hosts"),
                size=24,
                orientation="horizontal",
            ),
        ),
    ]


def _single_folder_rule_match_condition():
    return (
        "match_folder",
        FolderChoice(
            title=_("Match folder"),
            help=_(
                "This condition makes the rule match only hosts that are managed "
                "via WATO and that are contained in this folder - either directly "
                "or in one of its subfolders."
            ),
        ),
    )


def get_search_expression():
    search = request.get_str_input("search")
    if search is not None:
        search = search.strip().lower()
    return search


def get_hostnames_from_checkboxes(
    filterfunc: _Optional[Callable] = None, deflt: bool = False
) -> List[str]:
    """Create list of all host names that are select with checkboxes in the current file.
    This is needed for bulk operations."""
    selected = user.get_rowselection(
        weblib.selection_id(), "wato-folder-/" + _hosts_and_folders.Folder.current().path()
    )
    search_text = request.var("search")

    selected_host_names: List[str] = []
    for host_name, host in sorted(_hosts_and_folders.Folder.current().hosts().items()):
        if (not search_text or _search_text_matches(host, search_text)) and (
            "_c_" + host_name
        ) in selected:
            if filterfunc is None or filterfunc(host):
                selected_host_names.append(host_name)
    return selected_host_names


def _search_text_matches(
    host: _hosts_and_folders.CREHost,
    search_text: str,
) -> bool:

    match_regex = re.compile(search_text, re.IGNORECASE)
    for pattern in [
        host.name(),
        host.effective_attributes().get("ipaddress"),
        host.site_id(),
        get_site_config(host.site_id())["alias"],
        str(host.tag_groups()),
        str(host.labels()),
    ]:
        if match_regex.search(pattern):
            return True
    return False


def get_hosts_from_checkboxes(filterfunc=None):
    """Create list of all host objects that are select with checkboxes in the current file.
    This is needed for bulk operations."""
    folder = _hosts_and_folders.Folder.current()
    return [folder.host(host_name) for host_name in get_hostnames_from_checkboxes(filterfunc)]


class FullPathFolderChoice(DropdownChoice):
    def __init__(self, **kwargs):
        kwargs["choices"] = _hosts_and_folders.Folder.folder_choices_fulltitle
        kwargs.setdefault("title", _("Folder"))
        DropdownChoice.__init__(self, **kwargs)


class FolderChoice(DropdownChoice):
    def __init__(self, **kwargs):
        kwargs["choices"] = _hosts_and_folders.Folder.folder_choices
        kwargs.setdefault("title", _("Folder"))
        DropdownChoice.__init__(self, **kwargs)


@request_memoize()
def get_check_information() -> Mapping[CheckPluginName, Mapping[str, str]]:
    raw_check_dict = get_check_information_automation().plugin_infos
    return {CheckPluginName(name): info for name, info in sorted(raw_check_dict.items())}


@request_memoize()
def get_section_information() -> Mapping[str, Mapping[str, str]]:
    return get_section_information_automation().section_infos


def check_icmp_params():
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
