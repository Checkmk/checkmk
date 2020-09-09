#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for WATO internals and the WATO plugins"""

# TODO: More feature related splitting up would be better

import os
import abc
import json
import re
import subprocess
from typing import Callable, List, Type, Optional as _Optional, Tuple as _Tuple

from six import ensure_str

import cmk.utils.plugin_registry

import cmk.gui.mkeventd
import cmk.gui.config as config
from cmk.gui.config import SiteId, SiteConfiguration, SiteConfigurations
import cmk.gui.userdb as userdb
import cmk.gui.backup as backup
import cmk.gui.hooks as hooks
import cmk.gui.weblib as weblib
from cmk.gui.pages import page_registry
from cmk.gui.i18n import _u, _
from cmk.gui.globals import html, g
from cmk.gui.htmllib import Choices, HTML
from cmk.gui.exceptions import MKUserError, MKGeneralException
from cmk.gui.valuespec import (  # noqa: F401 # pylint: disable=unused-import
    ABCPageListOfMultipleGetChoice, Alternative, CascadingDropdown, Checkbox, Dictionary,
    DocumentationURL, DropdownChoice, DualListChoice, ElementSelection, FixedValue, Float, Integer,
    Labels, ListChoice, ListOf, ListOfMultiple, ListOfStrings, MonitoredHostname,
    OptionalDropdownChoice, Password, Percentage, RegExp, RegExpUnicode, RuleComment, TextAscii,
    TextAsciiAutocomplete, TextUnicode, Transform, Tuple, Url, ValueSpec, ValueSpecHelp,
    rule_option_elements, SingleLabel,
)
from cmk.gui.plugins.wato.utils.base_modes import (  # noqa: F401 # pylint: disable=unused-import
    ActionResult, WatoMode,
)
from cmk.gui.plugins.wato.utils.simple_modes import (  # noqa: F401 # pylint: disable=unused-import
    SimpleEditMode, SimpleListMode, SimpleModeType,
)
from cmk.gui.plugins.wato.utils.html_elements import (  # noqa: F401 # pylint: disable=unused-import
    search_form, wato_confirm,
)
from cmk.gui.plugins.wato.utils.main_menu import (  # noqa: F401 # pylint: disable=unused-import
    MainMenu, MainModule, MenuItem, WatoModule, main_module_registry, register_modules,
    MainModuleTopic, MainModuleTopicHosts, MainModuleTopicServices, MainModuleTopicBI,
    MainModuleTopicAgents, MainModuleTopicEvents, MainModuleTopicUsers, MainModuleTopicGeneral,
    MainModuleTopicMaintenance, MainModuleTopicCustom,
)
import cmk.gui.watolib as watolib
from cmk.gui.watolib.password_store import PasswordStore
from cmk.gui.watolib.timeperiods import TimeperiodSelection  # noqa: F401 # pylint: disable=unused-import
from cmk.gui.watolib.users import notification_script_title
from cmk.gui.groups import (
    load_contact_group_information,
    load_host_group_information,
    load_service_group_information,
)
from cmk.gui.watolib.rulespecs import (  # noqa: F401 # pylint: disable=unused-import
    BinaryHostRulespec, BinaryServiceRulespec, CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem, HostRulespec, ManualCheckParameterRulespec, Rulespec,
    RulespecGroup, RulespecGroupManualChecksApplications, RulespecGroupManualChecksEnvironment,
    RulespecGroupManualChecksHardware, RulespecGroupManualChecksNetworking,
    RulespecGroupManualChecksOperatingSystem, RulespecGroupManualChecksStorage,
    RulespecGroupManualChecksVirtualization, RulespecSubGroup, ServiceRulespec, TimeperiodValuespec,
    rulespec_group_registry, rulespec_registry,
)
from cmk.gui.watolib.host_attributes import (  # noqa: F401 # pylint: disable=unused-import
    ABCHostAttributeNagiosText, ABCHostAttributeValueSpec, HostAttributeTopicAddress,
    HostAttributeTopicBasicSettings, HostAttributeTopicCustomAttributes,
    HostAttributeTopicDataSources, HostAttributeTopicHostTags, HostAttributeTopicManagementBoard,
    HostAttributeTopicMetaData, HostAttributeTopicNetworkScan, host_attribute_registry,
    host_attribute_topic_registry,
)
from cmk.gui.watolib import (  # noqa: F401 # pylint: disable=unused-import
    ABCConfigDomain, ACResult, ACResultCRIT, ACResultOK, ACResultWARN, ACTest, ACTestCategories,
    ConfigDomainCACertificates, ConfigDomainCore, ConfigDomainEventConsole, ConfigDomainGUI,
    ConfigDomainOMD, LivestatusViaTCP, ac_test_registry, add_change, add_replication_paths,
    config_domain_registry, folder_preserving_link, get_rulegroup, is_wato_slave_site, log_audit,
    make_action_link, multisite_dir, register_rule, site_neutral_path, user_script_choices,
    user_script_title, wato_fileheader, wato_root_dir,
)
from cmk.gui.watolib.config_sync import (  # noqa: F401 # pylint: disable=unused-import
    ReplicationPath,)
from cmk.gui.plugins.watolib.utils import (  # noqa: F401 # pylint: disable=unused-import
    ConfigVariable, ConfigVariableGroup, SampleConfigGenerator, config_variable_group_registry,
    config_variable_registry, register_configvar, sample_config_generator_registry,
)

from cmk.gui.watolib.wato_background_job import WatoBackgroundJob  # noqa: F401 # pylint: disable=unused-import

import cmk.gui.forms as forms
from cmk.gui.permissions import (
    PermissionSection,
    permission_section_registry,
)


@permission_section_registry.register
class PermissionSectionWATO(PermissionSection):
    @property
    def name(self):
        return "wato"

    @property
    def title(self):
        return _("WATO - Checkmk's Web Administration Tool")


def PluginCommandLine():
    def _validate_custom_check_command_line(value, varprefix):
        if "--pwstore=" in value:
            raise MKUserError(
                varprefix, _("You are not allowed to use passwords from the password store here."))

    return TextAscii(
        title=_("Command line"),
        help=
        _("Please enter the complete shell command including path name and arguments to execute. "
          "If the plugin you like to execute is located in either <tt>~/local/lib/nagios/plugins</tt> "
          "or <tt>~/lib/nagios/plugins</tt> within your site directory, you can strip the path name and "
          "just configure the plugin file name as command <tt>check_foobar</tt>.") +
        monitoring_macro_help(),
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
        "the macro <tt>$_HOSTFOO$</tt> being replaced with <tt>bar</tt> ")


def UserIconOrAction(title: str, help: str) -> DropdownChoice:  # pylint: disable=redefined-builtin
    empty_text = _("In order to be able to choose actions here, you need to "
                   "<a href=\"%s\">define your own actions</a>.") % \
                      "wato.py?mode=edit_configvar&varname=user_icons_and_actions"

    return DropdownChoice(
        title=title,
        choices=_list_user_icons_and_actions,
        empty_text=empty_text,
        help=help + ' ' + empty_text,
    )


def _list_user_icons_and_actions():
    choices = []
    for key, action in config.user_icons_and_actions.items():
        label = key
        if 'title' in action:
            label += ' - ' + action['title']
        if 'url' in action:
            label += ' (' + action['url'][0] + ')'

        choices.append((key, label))
    return sorted(choices, key=lambda x: x[1])


def SNMPCredentials(  # pylint: disable=redefined-builtin
        title: _Optional[str] = None,
        help: _Optional[ValueSpecHelp] = None,
        only_v3: bool = False,
        default_value: _Optional[str] = "public",
        allow_none: bool = False,
        for_ec: bool = False) -> Alternative:
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

    elements.extend([
        _snmpv1_v2_credentials_element(),
        _snmpv3_no_auth_no_priv_credentials_element(),
        _snmpv3_auth_no_priv_credentials_element(),
        _snmpv3_auth_priv_credentials_element(for_ec=for_ec),
    ])

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
        None,
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
        Tuple(
            title=_("Credentials for SNMPv3 without authentication and privacy (noAuthNoPriv)"),
            elements=[
                FixedValue(
                    "noAuthNoPriv",
                    title=_("Security Level"),
                    totext=_("No authentication, no privacy"),
                ),
                TextAscii(title=_("Security name"), attrencode=True, allow_empty=False),
            ],
        ),
        forth=lambda x: x if (x and len(x) == 2) else ("noAuthNoPriv", ""),
    )


def _snmpv3_auth_no_priv_credentials_element() -> ValueSpec:
    return Tuple(
        title=_("Credentials for SNMPv3 with authentication but without privacy (authNoPriv)"),
        elements=[
            FixedValue(
                "authNoPriv",
                title=_("Security Level"),
                totext=_("authentication but no privacy"),
            ),
        ] + _snmpv3_auth_protocol_elements(),
    )


def _snmpv3_auth_priv_credentials_element(for_ec: bool = False) -> ValueSpec:
    priv_protocol_choices = [
        ("DES", _("CBC-DES")),
        ("AES", _("AES-128")),
    ]
    if for_ec:
        # TODO Remove this var once we use pysnmp in all places
        # EC uses pysnmp which supports these protocols
        # netsnmp/inline + classic does not support these protocols
        priv_protocol_choices.extend([
            ("3DES-EDE", _("3DES-EDE")),
            ("AES-192", _("AES-192")),
            ("AES-256", _("AES-256")),
            ("AES-192-Blumenthal", _("AES-192-Blumenthal")),
            ("AES-256-Blumenthal", _("AES-256-Blumenthal")),
        ])

    return Tuple(
        title=_("Credentials for SNMPv3 with authentication and privacy (authPriv)"),
        elements=[
            FixedValue(
                "authPriv",
                title=_("Security Level"),
                totext=_("authentication and encryption"),
            ),
        ] + _snmpv3_auth_protocol_elements() + [
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
        TextAscii(
            title=_("Security name"),
            attrencode=True,
        ),
        Password(
            title=_("Authentication password"),
            minlen=8,
        )
    ]


def IPMIParameters() -> Dictionary:
    return Dictionary(
        title=_("IPMI credentials"),
        elements=[
            ("username", TextAscii(
                title=_("Username"),
                allow_empty=False,
            )),
            ("password", Password(
                title=_("Password"),
                allow_empty=False,
            )),
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
        elements=[
            ("drop_domain",
             FixedValue(
                 True,
                 title=_("Convert FQHN"),
                 totext=_("Drop domain part (<tt>host123.foobar.de</tt> &#8594; <tt>host123</tt>)"),
             )),
        ] + _translation_elements("host"))


def ServiceDescriptionTranslation(**kwargs):
    help_txt = kwargs.get("help")
    title = kwargs.get("title")
    return Dictionary(
        title=title,
        help=help_txt,
        elements=_translation_elements("service"),
    )


def _translation_elements(what):
    if what == "host":
        singular = "hostname"
        plural = "hostnames"

    elif what == "service":
        singular = "service description"
        plural = "service descriptions"

    else:
        raise MKGeneralException("No translations found for %s." % what)

    return [
        ("case",
         DropdownChoice(title=_("Case translation"),
                        choices=[
                            (None, _("Do not convert case")),
                            ("upper", _("Convert %s to upper case") % plural),
                            ("lower", _("Convert %s to lower case") % plural),
                        ])),
        ("regex",
         Transform(
             ListOf(
                 Tuple(
                     orientation="horizontal",
                     elements=[
                         RegExpUnicode(
                             title=_("Regular expression"),
                             help=_("Must contain at least one subgroup <tt>(...)</tt>"),
                             mingroups=0,
                             maxgroups=9,
                             size=30,
                             allow_empty=False,
                             mode=RegExp.prefix,
                             case_sensitive=False,
                         ),
                         TextUnicode(
                             title=_("Replacement"),
                             help=_(
                                 "Use <tt>\\1</tt>, <tt>\\2</tt> etc. to replace matched subgroups"
                             ),
                             size=30,
                             allow_empty=False,
                         )
                     ],
                 ),
                 title=_("Multiple regular expressions"),
                 help=
                 _("You can add any number of expressions here which are executed succesively until the first match. "
                   "Please specify a regular expression in the first field. This expression should at "
                   "least contain one subexpression exclosed in brackets - for example <tt>vm_(.*)_prod</tt>. "
                   "In the second field you specify the translated %s and can refer to the first matched "
                   "group with <tt>\\1</tt>, the second with <tt>\\2</tt> and so on, for example <tt>\\1.example.org</tt>. "
                   "") % singular,
                 add_label=_("Add expression"),
                 movable=False,
             ),
             forth=lambda x: isinstance(x, tuple) and [x] or x,
         )),
        ("mapping",
         ListOf(
             Tuple(
                 orientation="horizontal",
                 elements=[
                     TextUnicode(
                         title=_("Original %s") % singular,
                         size=30,
                         allow_empty=False,
                         attrencode=True,
                     ),
                     TextUnicode(
                         title=_("Translated %s") % singular,
                         size=30,
                         allow_empty=False,
                         attrencode=True,
                     ),
                 ],
             ),
             title=_("Explicit %s mapping") % singular,
             help=_(
                 "If case conversion and regular expression do not work for all cases then you can "
                 "specify explicity pairs of origin {0} and translated {0} here. This "
                 "mapping is being applied <b>after</b> the case conversion and <b>after</b> a regular "
                 "expression conversion (if that matches).").format(singular),
             add_label=_("Add new mapping"),
             movable=False,
         )),
    ]


# TODO: Refactor this and all other childs of ElementSelection() to base on
#       DropdownChoice(). Then remove ElementSelection()
class _GroupSelection(ElementSelection):
    def __init__(self, what, choices, no_selection=None, **kwargs):
        kwargs.setdefault(
            'empty_text',
            _('You have not defined any %s group yet. Please '
              '<a href="wato.py?mode=edit_%s_group">create</a> at least one first.') % (what, what))
        super(_GroupSelection, self).__init__(**kwargs)
        self._what = what
        self._choices = choices
        self._no_selection = no_selection

    def get_elements(self):
        elements = self._choices()
        if self._no_selection:
            # Beware: ElementSelection currently can only handle string
            # keys, so we cannot take 'None' as a value.
            elements.append(('', self._no_selection))
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


def _sorted_contact_group_choices():
    cache_id = "sorted_contact_group_choices"
    if cache_id not in g:
        g.cache_id = _group_choices(load_contact_group_information())
    return g.cache_id


def _sorted_service_group_choices():
    cache_id = "sorted_service_group_choices"
    if cache_id not in g:
        g.cache_id = _group_choices(load_service_group_information())
    return g.cache_id


def _sorted_host_group_choices():
    cache_id = "sorted_host_group_choices"
    if cache_id not in g:
        g.cache_id = _group_choices(load_host_group_information())
    return g.cache_id


def _group_choices(group_information):
    return sorted([(k, t['alias'] and t['alias'] or k) for (k, t) in group_information.items()],
                  key=lambda x: x[1].lower())


def passwordstore_choices():
    pw_store = PasswordStore()
    return [(ident, pw["title"])
            for ident, pw in pw_store.filter_usable_entries(pw_store.load_for_reading()).items()]


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
            ("password", _("Explicit"), Password(
                allow_empty=allow_empty,
                size=size,
            )),
            ("store", _("From password store"),
             DropdownChoice(
                 choices=passwordstore_choices,
                 sorted=True,
                 invalid_choice="complain",
                 invalid_choice_title=_("Password does not exist or using not permitted"),
                 invalid_choice_error=_("The configured password has either be removed or you "
                                        "are not permitted to use this password. Please choose "
                                        "another one."),
             )),
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
        PasswordFromStore(
            title=title,
            help=help,
            allow_empty=allow_empty,
            size=size,
        ),
        forth=lambda v: ("password", v) if not isinstance(v, tuple) else v,
    )


def HTTPProxyReference():
    """Use this valuespec in case you want the user to configure a HTTP proxy
    The configured value is is used for preparing requests to work in a proxied environment."""
    def _global_proxy_choices():
        settings = watolib.ConfigDomainCore().load()
        return [(p["ident"], p["title"]) for p in settings.get("http_proxies", {}).values()]

    return CascadingDropdown(
        title=_("HTTP proxy"),
        default_value=("environment", "environment"),
        choices=[
            ("environment", _("Use from environment"),
             FixedValue(
                 "environment",
                 help=
                 _("Use the proxy settings from the environment variables. The variables <tt>NO_PROXY</tt>, "
                   "<tt>HTTP_PROXY</tt> and <tt>HTTPS_PROXY</tt> are taken into account during execution. "
                   "Have a look at the python requests module documentation for further information. Note "
                   "that these variables must be defined as a site-user in ~/etc/environment and that "
                   "this might affect other notification methods which also use the requests module."
                  ),
                 totext=_("Use proxy settings from the process environment"),
             )),
            ("no_proxy", _("Connect without proxy"),
             FixedValue(
                 None,
                 totext=_("Connect directly to the destination instead of using a proxy. "
                          "This is the default."),
             )),
            ("global", _("Use globally configured proxy"),
             DropdownChoice(
                 choices=_global_proxy_choices,
                 sorted=True,
             )),
            ("url", _("Use explicit proxy settings"), HTTPProxyInput()),
        ],
        sorted=False,
    )


def HTTPProxyInput():
    """Use this valuespec in case you want the user to input a HTTP proxy setting"""
    return Url(
        title=_("Proxy URL"),
        default_scheme="http",
        allowed_schemes=["http", "https", "socks4", "socks4a", "socks5", "socks5h"],
    )


def register_check_parameters(subgroup,
                              checkgroup,
                              title,
                              valuespec,
                              itemspec,
                              match_type,
                              has_inventory=True,
                              register_static_check=True,
                              deprecated=False):
    """Legacy registration of check parameters"""
    if valuespec and isinstance(valuespec, Dictionary) and match_type != "dict":
        raise MKGeneralException(
            "Check parameter definition for %s has type Dictionary, but match_type %s" %
            (checkgroup, match_type))

    if not valuespec:
        raise NotImplementedError()

    # Added during 1.6 development for easier transition. Convert all legacy subgroup
    # parameters (which are either str/unicode to group classes
    if isinstance(subgroup, str):
        subgroup = get_rulegroup("checkparams/" + subgroup).__class__

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

        base_class = CheckParameterRulespecWithItem if itemspec is not None else CheckParameterRulespecWithoutItem

        rulespec_registry.register(base_class(**kwargs))

    if not (valuespec and has_inventory) and register_static_check:
        raise MKGeneralException("Sorry, registering manual check parameters without discovery "
                                 "check parameters is not supported anymore using the old API. "
                                 "Please register the manual check rulespec using the new API. "
                                 "Checkgroup: %s" % checkgroup)


@rulespec_group_registry.register
class RulespecGroupMonitoringConfiguration(RulespecGroup):
    @property
    def name(self):
        return "monconf"

    @property
    def title(self):
        return _("Service monitoring rules")

    @property
    def help(self):
        return _("Rules to configure existing services in the monitoring. For "
                 "example, threshold values can be set, the execution time for "
                 "active checks can be configured or attributes such as labels "
                 "or tags can be assigned to the services.")


@rulespec_group_registry.register
class RulespecGroupDiscoveryCheckParameters(RulespecGroup):
    @property
    def name(self):
        return "checkparams"

    @property
    def title(self):
        return _("Service discovery rules")

    @property
    def help(self):
        return _("Rules that influence the discovery of services. These rules "
                 "allow, for example, the execution of a periodic service "
                 "discovery or the deactivation of check plugins and services. "
                 "Additionally, the discovery of individual check plugins like "
                 "for example the interface check plugin can "
                 "be customized.")


@rulespec_group_registry.register
class RulespecGroupCheckParametersNetworking(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self):
        return "networking"

    @property
    def title(self):
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
    def title(self):
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
    def title(self):
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
    def title(self):
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
    def title(self):
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
    def title(self):
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
    def title(self):
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
    def title(self):
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
    def title(self):
        return _("Discovery of individual services")


# The following function looks like a value spec and in fact
# can be used like one (but take no parameters)
def PredictiveLevels(**args):
    dif = args.get("default_difference", (2.0, 4.0))
    unitname = args.get("unit", "")
    if unitname:
        unitname += " "

    return Dictionary(
        title=_("Predictive Levels (only on CMC)"),
        optional_keys=[
            "weight", "levels_upper", "levels_upper_min", "levels_lower", "levels_lower_max"
        ],
        default_keys=["levels_upper"],
        columns=1,
        headers="sup",
        elements=[
            ("period",
             DropdownChoice(title=_("Base prediction on"),
                            choices=[
                                ("wday", _("Day of the week (1-7, 1 is Monday)")),
                                ("day", _("Day of the month (1-31)")),
                                ("hour", _("Hour of the day (0-23)")),
                                ("minute", _("Minute of the hour (0-59)")),
                            ])),
            ("horizon",
             Integer(
                 title=_("Time horizon"),
                 unit=_("days"),
                 minvalue=1,
                 default_value=90,
             )),
            # ( "weight",
            #   Percentage(
            #       title = _("Raise weight of recent time"),
            #       label = _("by"),
            #       default_value = 0,
            # )),
            ("levels_upper",
             CascadingDropdown(
                 title=_("Dynamic levels - upper bound"),
                 choices=[
                     ("absolute", _("Absolute difference from prediction"),
                      Tuple(elements=[
                          Float(title=_("Warning at"),
                                unit=unitname + _("above predicted value"),
                                default_value=dif[0]),
                          Float(title=_("Critical at"),
                                unit=unitname + _("above predicted value"),
                                default_value=dif[1]),
                      ])),
                     ("relative", _("Relative difference from prediction"),
                      Tuple(elements=[
                          Percentage(title=_("Warning at"),
                                     unit=_("% above predicted value"),
                                     default_value=10),
                          Percentage(title=_("Critical at"),
                                     unit=_("% above predicted value"),
                                     default_value=20),
                      ])),
                     ("stdev", _("In relation to standard deviation"),
                      Tuple(elements=[
                          Float(title=_("Warning at"),
                                unit=_("times the standard deviation above the predicted value"),
                                default_value=2.0),
                          Float(title=_("Critical at"),
                                unit=_("times the standard deviation above the predicted value"),
                                default_value=4.0),
                      ])),
                 ])),
            ("levels_upper_min",
             Tuple(
                 title=_("Limit for upper bound dynamic levels"),
                 help=_(
                     "Regardless of how the dynamic levels upper bound are computed according to the prediction: "
                     "the will never be set below the following limits. This avoids false alarms "
                     "during times where the predicted levels would be very low."),
                 elements=[
                     Float(title=_("Warning level is at least"), unit=unitname),
                     Float(title=_("Critical level is at least"), unit=unitname),
                 ])),
            ("levels_lower",
             CascadingDropdown(
                 title=_("Dynamic levels - lower bound"),
                 choices=[
                     ("absolute", _("Absolute difference from prediction"),
                      Tuple(elements=[
                          Float(title=_("Warning at"),
                                unit=unitname + _("below predicted value"),
                                default_value=2.0),
                          Float(title=_("Critical at"),
                                unit=unitname + _("below predicted value"),
                                default_value=4.0),
                      ])),
                     ("relative", _("Relative difference from prediction"),
                      Tuple(elements=[
                          Percentage(title=_("Warning at"),
                                     unit=_("% below predicted value"),
                                     default_value=10),
                          Percentage(title=_("Critical at"),
                                     unit=_("% below predicted value"),
                                     default_value=20),
                      ])),
                     ("stdev", _("In relation to standard deviation"),
                      Tuple(elements=[
                          Float(title=_("Warning at"),
                                unit=_("times the standard deviation below the predicted value"),
                                default_value=2.0),
                          Float(title=_("Critical at"),
                                unit=_("times the standard deviation below the predicted value"),
                                default_value=4.0),
                      ])),
                 ])),
        ])


# To be used as ValueSpec for levels on numeric values, with
# prediction
def Levels(**kwargs):
    def match_levels_alternative(v):
        if isinstance(v, dict):
            return 2
        if isinstance(v, tuple) and v != (None, None):
            return 1
        return 0

    help_txt = kwargs.get("help")
    unit = kwargs.get("unit", "")
    if not isinstance(unit, str):
        raise Exception("illegal unit for Levels: %r" % (unit,))
    title = kwargs.get("title")
    default_levels = kwargs.get("default_levels", (0.0, 0.0))
    default_difference = kwargs.get("default_difference", (0, 0))
    default_value = kwargs.get("default_value", default_levels if default_levels else None)

    return Alternative(
        title=title,
        help=help_txt,
        elements=[
            FixedValue(
                None,
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
            PredictiveLevels(default_difference=default_difference,),
        ],
        match=match_levels_alternative,
        default_value=default_value,
    )


def may_edit_ruleset(varname):
    if varname == "ignored_services":
        return config.user.may("wato.services") or config.user.may("wato.rulesets")
    if varname in [
            "custom_checks",
            "datasource_programs",
            "agent_config:mrpe",
            "agent_config:agent_paths",
            "agent_config:runas",
            "agent_config:only_from",
    ]:
        return config.user.may("wato.rulesets") and config.user.may(
            "wato.add_or_modify_executables")
    if varname == "agent_config:custom_files":
        return config.user.may("wato.rulesets") and config.user.may(
            "wato.agent_deploy_custom_files")
    return config.user.may("wato.rulesets")


class CheckTypeSelection(DualListChoice):
    def __init__(self, **kwargs):
        super(CheckTypeSelection, self).__init__(rows=25, **kwargs)

    def get_elements(self):
        checks = get_check_information()
        elements = sorted([
            (cn, (cn + " - " + ensure_str(c["title"]))[:60]) for (cn, c) in checks.items()
        ])
        return elements


class ConfigHostname(TextAsciiAutocomplete):
    """Hostname input with dropdown completion

    Renders an input field for entering a host name while providing an auto completion dropdown field.
    Fetching the choices from the current WATO config"""
    ident = "monitored_hostname"

    def __init__(self, **kwargs):
        super(ConfigHostname, self).__init__(completion_ident=self.ident,
                                             completion_params={},
                                             **kwargs)

    @classmethod
    def autocomplete_choices(cls, value, params):
        """Return the matching list of dropdown choices
        Called by the webservice with the current input field value and the completions_params to get the list of choices"""
        all_hosts = watolib.Host.all()
        match_pattern = re.compile(value, re.IGNORECASE)
        match_list = []
        for host_name, host_object in all_hosts.items():
            if match_pattern.search(host_name) is not None and host_object.may("read"):
                match_list.append(tuple((host_name, host_name)))

        return match_list


class ABCEventsMode(WatoMode, metaclass=abc.ABCMeta):
    @classmethod
    @abc.abstractmethod
    def _rule_match_conditions(cls):
        raise NotImplementedError()

    # flavour = "notify" or "alert"
    @classmethod
    def _event_rule_match_conditions(cls, flavour):
        if flavour == "notify":
            add_choices = [
                ('f', _("Start or end of flapping state")),
                ('s', _("Start or end of a scheduled downtime")),
                ('x', _("Acknowledgement of problem")),
                ('as', _("Alert handler execution, successful")),
                ('af', _("Alert handler execution, failed")),
            ]
            add_default = ['f', 's', 'x', 'as', 'af']
        else:
            add_choices = []
            add_default = []

        return [
            ("match_host_event",
             ListChoice(
                 title=_("Match host event type"),
                 help=
                 (_("Select the host event types and transitions this rule should handle.<br>"
                    "Note: If you activate this option and do <b>not</b> also specify service event "
                    "types then this rule will never hold for service notifications!<br>"
                    "Note: You can only match on event types <a href=\"%s\">created by the core</a>."
                   ) % "wato.py?mode=edit_ruleset&varname=extra_host_conf%3Anotification_options"),
                 choices=[
                     ('rd', _("UP") + u" ➤ " + _("DOWN")),
                     ('ru', _("UP") + u" ➤ " + _("UNREACHABLE")),
                     ('dr', _("DOWN") + u" ➤ " + _("UP")),
                     ('du', _("DOWN") + u" ➤ " + _("UNREACHABLE")),
                     ('ud', _("UNREACHABLE") + u" ➤ " + _("DOWN")),
                     ('ur', _("UNREACHABLE") + u" ➤ " + _("UP")),
                     ('?r', _("any") + u" ➤ " + _("UP")),
                     ('?d', _("any") + u" ➤ " + _("DOWN")),
                     ('?u', _("any") + u" ➤ " + _("UNREACHABLE")),
                 ] + add_choices,
                 default_value=[
                     'rd',
                     'dr',
                 ] + add_default,
             )),
            ("match_service_event",
             ListChoice(
                 title=_("Match service event type"),
                 help=(_(
                     "Select the service event types and transitions this rule should handle.<br>"
                     "Note: If you activate this option and do <b>not</b> also specify host event "
                     "types then this rule will never hold for host notifications!<br>"
                     "Note: You can only match on event types <a href=\"%s\">created by the core</a>."
                 ) % "wato.py?mode=edit_ruleset&varname=extra_service_conf%3Anotification_options"),
                 choices=[
                     ('rw', _("OK") + u" ➤ " + _("WARN")),
                     ('rr', _("OK") + u" ➤ " + _("OK")),
                     ('rc', _("OK") + u" ➤ " + _("CRIT")),
                     ('ru', _("OK") + u" ➤ " + _("UNKNOWN")),
                     ('wr', _("WARN") + u" ➤ " + _("OK")),
                     ('wc', _("WARN") + u" ➤ " + _("CRIT")),
                     ('wu', _("WARN") + u" ➤ " + _("UNKNOWN")),
                     ('cr', _("CRIT") + u" ➤ " + _("OK")),
                     ('cw', _("CRIT") + u" ➤ " + _("WARN")),
                     ('cu', _("CRIT") + u" ➤ " + _("UNKNOWN")),
                     ('ur', _("UNKNOWN") + u" ➤ " + _("OK")),
                     ('uw', _("UNKNOWN") + u" ➤ " + _("WARN")),
                     ('uc', _("UNKNOWN") + u" ➤ " + _("CRIT")),
                     ('?r', _("any") + u" ➤ " + _("OK")),
                     ('?w', _("any") + u" ➤ " + _("WARN")),
                     ('?c', _("any") + u" ➤ " + _("CRIT")),
                     ('?u', _("any") + u" ➤ " + _("UNKNOWN")),
                 ] + add_choices,
                 default_value=[
                     'rw',
                     'rc',
                     'ru',
                     'wc',
                     'wu',
                     'uc',
                 ] + add_default,
             )),
        ]

    @classmethod
    def _generic_rule_match_conditions(cls):
        return _simple_host_rule_match_conditions() + [
            ("match_servicelabels",
             Labels(
                 Labels.World.CORE,
                 title=_("Match Service Labels"),
                 help=_(
                     "Use this condition to select hosts based on the configured service labels."),
             )),
            ("match_servicegroups",
             ServiceGroupChoice(
                 title=_("Match Service Groups"),
                 help=_(
                     "The service must be in one of the selected service groups. For host events this condition "
                     "never matches as soon as at least one group is selected."),
                 allow_empty=False,
             )),
            ("match_exclude_servicegroups",
             ServiceGroupChoice(
                 title=_("Exclude Service Groups"),
                 help=_(
                     "The service must not be in one of the selected service groups. For host events this condition "
                     "is simply ignored."),
                 allow_empty=False,
             )),
            ("match_servicegroups_regex",
             Tuple(
                 title=_("Match Service Groups (regex)"),
                 elements=[
                     DropdownChoice(choices=[("match_id", _("Match the internal identifier")),
                                             ("match_alias", _("Match the alias"))],
                                    default_value="match_id"),
                     ListOfStrings(
                         help=
                         _("The service group alias must match one of the following regular expressions."
                           " For host events this condition never matches as soon as at least one group is selected."
                          ),
                         valuespec=RegExpUnicode(
                             size=32,
                             mode=RegExpUnicode.infix,
                         ),
                         orientation="horizontal",
                     )
                 ])),
            ("match_exclude_servicegroups_regex",
             Tuple(
                 title=_("Exclude Service Groups (regex)"),
                 elements=[
                     DropdownChoice(choices=[("match_id", _("Match the internal identifier")),
                                             ("match_alias", _("Match the alias"))],
                                    default_value="match_id"),
                     ListOfStrings(
                         help=_(
                             "The service group alias must not match one of the following regular expressions. "
                             "For host events this condition is simply ignored."),
                         valuespec=RegExpUnicode(
                             size=32,
                             mode=RegExpUnicode.infix,
                         ),
                         orientation="horizontal",
                     )
                 ])),
            ("match_services",
             ListOfStrings(
                 title=_("Match only the following services"),
                 help=
                 _("Specify a list of regular expressions that must match the <b>beginning</b> of the "
                   "service name in order for the rule to match. Note: Host notifications never match this "
                   "rule if this option is being used."),
                 valuespec=RegExpUnicode(
                     size=32,
                     mode=RegExpUnicode.prefix,
                 ),
                 orientation="horizontal",
                 allow_empty=False,
                 empty_text=
                 _("Please specify at least one service regex. Disable the option if you want to allow all services."
                  ),
             )),
            ("match_exclude_services",
             ListOfStrings(
                 title=_("Exclude the following services"),
                 valuespec=RegExpUnicode(
                     size=32,
                     mode=RegExpUnicode.prefix,
                 ),
                 orientation="horizontal",
             )),
            ("match_checktype",
             CheckTypeSelection(
                 title=_("Match the following check types"),
                 help=
                 _("Only apply the rule if the notification originates from certain types of check plugins. "
                   "Note: Host notifications never match this rule if this option is being used."),
             )),
            (
                "match_plugin_output",
                RegExp(
                    title=_("Match the output of the check plugin"),
                    help=_(
                        "This text is a regular expression that is being searched in the output "
                        "of the check plugins that produced the alert. It is not a prefix but an infix match."
                    ),
                    mode=RegExpUnicode.prefix,
                ),
            ),
            ("match_contacts",
             ListOf(
                 userdb.UserSelection(only_contacts=True),
                 title=_("Match Contacts"),
                 help=_("The host/service must have one of the selected contacts."),
                 movable=False,
                 allow_empty=False,
                 add_label=_("Add contact"),
             )),
            ("match_contactgroups",
             ContactGroupChoice(
                 title=_("Match Contact Groups"),
                 help=_(
                     "The host/service must be in one of the selected contact groups. This only works with Check_MK Micro Core. "
                     "If you don't use the CMC that filter will not apply"),
                 allow_empty=False,
             )),
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
                        DropdownChoice(label=_("from:"),
                                       choices=cmk.gui.mkeventd.service_levels,
                                       prefix_values=True),
                        DropdownChoice(label=_(" to:"),
                                       choices=cmk.gui.mkeventd.service_levels,
                                       prefix_values=True),
                    ],
                ),
            ),
            (
                "match_timeperiod",
                watolib.timeperiods.TimeperiodSelection(
                    title=_("Match only during timeperiod"),
                    help=_(
                        "Match this rule only during times where the selected timeperiod from the monitoring "
                        "system is active."),
                    no_preselect=True,
                    no_preselect_title=_("Select a timeperiod"),
                ),
            ),
        ]

    @abc.abstractmethod
    def _add_change(self, log_what, log_text):
        raise NotImplementedError()

    def _generic_rule_list_actions(self, rules, what, what_title, save_rules):
        if html.request.has_var("_delete"):
            nr = html.request.get_integer_input_mandatory("_delete")
            rule = rules[nr]
            c = wato_confirm(
                _("Confirm deletion of %s") % what_title,
                _("Do you really want to delete the %s <b>%d</b> <i>%s</i>?") %
                (what_title, nr, rule.get("description", "")))
            if c:
                self._add_change(what + "-delete-rule", _("Deleted %s %d") % (what_title, nr))
                del rules[nr]
                save_rules(rules)
            elif c is False:
                return ""
            else:
                return

        elif html.request.has_var("_move"):
            if html.check_transaction():
                from_pos = html.request.get_integer_input_mandatory("_move")
                to_pos = html.request.get_integer_input_mandatory("_index")
                rule = rules[from_pos]
                del rules[from_pos]  # make to_pos now match!
                rules[to_pos:to_pos] = [rule]
                save_rules(rules)
                self._add_change(what + "-move-rule",
                                 _("Changed position of %s %d") % (what_title, from_pos))


def sort_sites(sites: SiteConfigurations) -> List[_Tuple[SiteId, SiteConfiguration]]:
    """Sort given sites argument by local, followed by remote sites"""
    return sorted(sites.items(),
                  key=lambda sid_s:
                  (sid_s[1].get("replication") or "", sid_s[1].get("alias", ""), sid_s[0]))


class ModeRegistry(cmk.utils.plugin_registry.Registry[Type[WatoMode]]):
    def plugin_name(self, instance):
        return instance.name()


mode_registry = ModeRegistry()


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
def configure_attributes(new,
                         hosts,
                         for_what,
                         parent,
                         myself=None,
                         without_attributes=None,
                         varprefix="",
                         basic_attributes=None):
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
    for topic_id, topic_title in watolib.get_sorted_host_attribute_topics(for_what, new):
        topic_is_volatile = True  # assume topic is sometimes hidden due to dependencies

        forms.header(
            topic_title,
            isopen=topic_id in ["basic", "address", "data_sources"],
            table_id=topic_id,
            show_advanced_toggle=True,
        )

        if topic_id == "basic":
            for attr_varprefix, vs, default_value in basic_attributes:
                forms.section(_u(vs.title()))
                vs.render_input(attr_varprefix, default_value)

        for attr in watolib.get_sorted_host_attributes_by_topic(topic_id):
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
            inherited_from = None
            inherited_value = None
            has_inherited = False
            container = None

            if attr.show_inherited_value():
                if for_what in ["host", "cluster"]:
                    url = watolib.Folder.current().edit_url()

                container = parent  # container is of type Folder
                while container:
                    if attrname in container.attributes():
                        url = container.edit_url()
                        inherited_from = _("Inherited from ") + str(
                            html.render_a(container.title(), href=url))

                        inherited_value = container.attributes()[attrname]
                        has_inherited = True
                        if attr.is_tag_attribute:
                            inherited_tags["attr_%s" % attrname] = inherited_value
                        break

                    container = container.parent()

            if not container:  # We are the root folder - we inherit the default values
                inherited_from = _("Default value")
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
            if for_what == "folder" and attr.is_mandatory() \
                and myself \
                and some_host_hasnt_set(myself, attrname) \
                and not has_inherited:
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

            if (for_what in ["host", "cluster"] and
                    parent.locked_hosts()) or (for_what == "folder" and myself and myself.locked()):
                checkbox_code = None
            elif force_entry:
                checkbox_code = html.render_checkbox("ignored_" + checkbox_name,
                                                     disabled="disabled")
                checkbox_code += html.render_hidden_field(checkbox_name, "on")
            else:
                onclick = "cmk.wato.fix_visibility(); cmk.wato.toggle_attribute(this, '%s');" % attrname
                checkbox_kwargs = {"disabled": "disabled"} if disabled else {}
                checkbox_code = html.render_checkbox(checkbox_name,
                                                     active,
                                                     onclick=onclick,
                                                     **checkbox_kwargs)

            forms.section(_u(attr.title()),
                          checkbox=checkbox_code,
                          section_id="attr_" + attrname,
                          is_advanced=attr.is_advanced())
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
                html.open_div(id_="attr_entry_%s" % attrname,
                              style="display: none;" if not active else None)
                attr.render_input(varprefix, defvalue)
                html.close_div()

                html.open_div(class_="inherited",
                              id_="attr_default_%s" % attrname,
                              style="display: none;" if active else None)

            #
            # DIV with actual / inherited / default value
            #

            # in bulk mode we show inheritance only if *all* hosts inherit
            explanation = u""
            if for_what == "bulk":
                if num_haveit == 0:
                    explanation = u" (%s)" % inherited_from
                    value = inherited_value
                elif not unique:
                    explanation = _("This value differs between the selected hosts.")
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
                    html.write(content)
                    html.close_b()
                else:
                    html.b(_u(content))

            html.write_text(explanation)
            html.close_div()

        if topic_is_volatile:
            volatile_topics.append(topic_id)

    forms.end()

    dialog_properties = {
        "inherited_tags": inherited_tags,
        "check_attributes": list(
            set(dependency_mapping_tags.keys()) | set(dependency_mapping_roles.keys()) |
            set(hide_attributes)),
        "aux_tags_by_tag": config.tags.get_aux_tags_by_tag(),
        "depends_on_tags": dependency_mapping_tags,
        "depends_on_roles": dependency_mapping_roles,
        "volatile_topics": volatile_topics,
        "user_roles": config.user.role_ids,
        "hide_attributes": hide_attributes,
    }
    html.javascript("cmk.wato.prepare_edit_dialog(%s);"
                    "cmk.wato.fix_visibility();" % json.dumps(dialog_properties))


# Check if at least one host in a folder (or its subfolders)
# has not set a certain attribute. This is needed for the validation
# of mandatory attributes.
def some_host_hasnt_set(folder, attrname):
    # Check subfolders
    for subfolder in folder.subfolders():
        # If the attribute is not set in the subfolder, we need
        # to check all hosts and that folder.
        if attrname not in subfolder.attributes() \
            and some_host_hasnt_set(subfolder, attrname):
            return True

    # Check hosts in this folder
    for host in folder.hosts().values():
        if not host.has_explicit_attribute(attrname):
            return True

    return False


class SiteBackupJobs(backup.Jobs):
    def __init__(self):
        super(SiteBackupJobs, self).__init__(backup.site_config_path())

    def _apply_cron_config(self):
        p = subprocess.Popen(["omd", "restart", "crontab"],
                             close_fds=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             encoding="utf-8",
                             stdin=open(os.devnull))
        if p.wait() != 0:
            out = "Huh???" if p.stdout is None else p.stdout.read()
            raise MKGeneralException(_("Failed to apply the cronjob config: %s") % out)


# TODO: Kept for compatibility with pre-1.6 WATO plugins
def register_hook(name, func):
    hooks.register_from_plugin(name, func)


class NotificationParameter(metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def ident(self) -> str:
        raise NotImplementedError()

    @abc.abstractproperty
    def spec(self) -> Dictionary:
        raise NotImplementedError()


class NotificationParameterRegistry(cmk.utils.plugin_registry.Registry[Type[NotificationParameter]]
                                   ):
    def plugin_name(self, instance):
        return instance().ident

    def registration_hook(self, instance):
        plugin = instance()

        script_title = notification_script_title(plugin.ident)

        valuespec = plugin.spec
        # TODO: Cleanup this hack
        valuespec._title = _("Call with the following parameters:")

        register_rule(rulespec_group_registry["monconf/notifications"],
                      "notification_parameters:" + plugin.ident,
                      valuespec,
                      _("Parameters for %s") % script_title,
                      itemtype=None,
                      match="dict")


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
        super(DictHostTagCondition, self).__init__(
            ListOfMultiple(
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

    def _get_cached_tag_group_choices(self):
        # In case one has configured a lot of tag groups / id recomputing this for
        # every DictHostTagCondition instance takes a lot of time
        if "tag_group_choices" not in g:
            g.tag_group_choices = self._get_tag_group_choices()
        return g.tag_group_choices

    def _get_tag_group_choices(self):
        choices = []
        all_topics = config.tags.get_topic_choices()
        tag_groups_by_topic = dict(config.tags.get_tag_groups_by_topic())
        aux_tags_by_topic = dict(config.tags.get_aux_tags_by_topic())
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
            return self._single_tag_choice(tag_group_id=tag_group.id,
                                           choice_title=tag_group.choice_title,
                                           tag_id=tag_group.tags[0].id,
                                           title=tag_group.tags[0].title)

        tag_id_choice = ListOf(
            valuespec=DropdownChoice(choices=tag_choices,),
            style=ListOf.Style.FLOATING,
            add_label=_("Add tag"),
            del_label=_("Remove tag"),
            magic="@@#!#@@",
            movable=False,
            validate=lambda value, varprefix: self._validate_tag_list(value, varprefix, tag_choices
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
                    _("The tag '%s' is selected multiple times. A tag may be selected only once.") %
                    dict(tag_choices)[tag_id])
            seen.add(tag_id)

    def _get_aux_tag_choice(self, aux_tag):
        return self._single_tag_choice(tag_group_id=aux_tag.id,
                                       choice_title=aux_tag.choice_title,
                                       tag_id=aux_tag.id,
                                       title=aux_tag.title)

    def _single_tag_choice(self, tag_group_id, choice_title, tag_id, title):
        return (
            tag_group_id,
            Tuple(
                title=choice_title,
                elements=[
                    self._is_or_is_not(label=choice_title + " ",),
                    FixedValue(
                        tag_id,
                        title=_u(title),
                        totext=_u(title),
                    )
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
        return DropdownChoice(choices=[
            ("is", _("is")),
            ("is_not", _("is not")),
        ], **kwargs)


class HostTagCondition(ValueSpec):
    """ValueSpec for editing a tag-condition"""
    def render_input(self, varprefix, value):
        self._render_condition_editor(varprefix, value)

    def from_html_vars(self, varprefix):
        return self._get_tag_conditions(varprefix)

    def _get_tag_conditions(self, varprefix):
        """Retrieve current tag condition settings from HTML variables"""
        if varprefix:
            varprefix += "_"

        # Main tags
        tag_list = []
        for tag_group in config.tags.tag_groups:
            if tag_group.is_checkbox_tag_group:
                tagvalue = tag_group.default_value
            else:
                tagvalue = html.request.var(varprefix + "tagvalue_" + tag_group.id)

            mode = html.request.var(varprefix + "tag_" + tag_group.id)
            if mode == "is":
                tag_list.append(tagvalue)
            elif mode == "isnot":
                tag_list.append("!" + tagvalue)

        # Auxiliary tags
        for aux_tag in config.tags.aux_tag_list.get_tags():
            mode = html.request.var(varprefix + "auxtag_" + aux_tag.id)
            if mode == "is":
                tag_list.append(aux_tag.id)
            elif mode == "isnot":
                tag_list.append("!" + aux_tag.id)

        return tag_list

    def canonical_value(self):
        return []

    def value_to_text(self, value):
        return "|".join(value)

    def validate_datatype(self, value, varprefix):
        if not isinstance(value, list):
            raise MKUserError(varprefix,
                              _("The list of host tags must be a list, but "
                                "is %r") % type(value))
        for x in value:
            if not isinstance(x, str):
                raise MKUserError(
                    varprefix,
                    _("The list of host tags must only contain strings "
                      "but also contains %r") % x)

    def _render_condition_editor(self, varprefix, tag_specs):
        """Render HTML input fields for editing a tag based condition"""
        if varprefix:
            varprefix += "_"

        if not config.tags.get_tag_ids():
            html.write(_("You have not configured any <a href=\"wato.py?mode=tags\">tags</a>."))
            return

        tag_groups_by_topic = dict(config.tags.get_tag_groups_by_topic())
        aux_tags_by_topic = dict(config.tags.get_aux_tags_by_topic())

        all_topics = config.tags.get_topic_choices()
        make_foldable = len(all_topics) > 1

        for topic_id, topic_title in all_topics:
            if make_foldable:
                html.begin_foldable_container("topic", varprefix + topic_title, True,
                                              HTML("<b>%s</b>" % (_u(topic_title))))
            html.open_table(class_=["hosttags"])

            for tag_group in tag_groups_by_topic.get(topic_id, []):
                html.open_tr()
                html.open_td(class_="title")
                html.write("%s: &nbsp;" % _u(tag_group.title))
                html.close_td()

                choices = tag_group.get_tag_choices()
                default_tag, deflt = self._current_tag_setting(choices, tag_specs)
                self._tag_condition_dropdown(varprefix, "tag", deflt, tag_group.id)
                if tag_group.is_checkbox_tag_group:
                    html.write_text(" " + _("set"))
                else:
                    html.dropdown(varprefix + "tagvalue_" + tag_group.id,
                                  [(t[0], _u(t[1])) for t in choices if t[0] is not None],
                                  deflt=default_tag)

                html.close_div()
                html.close_td()
                html.close_tr()

            for aux_tag in aux_tags_by_topic.get(topic_id, []):
                html.open_tr()
                html.open_td(class_="title")
                html.write("%s: &nbsp;" % _u(aux_tag.title))
                html.close_td()
                default_tag, deflt = self._current_tag_setting([(aux_tag.id, _u(aux_tag.title))],
                                                               tag_specs)
                self._tag_condition_dropdown(varprefix, "auxtag", deflt, aux_tag.id)
                html.write_text(" " + _("set"))
                html.close_div()
                html.close_td()
                html.close_tr()

            html.close_table()
            if make_foldable:
                html.end_foldable_container()

    def _current_tag_setting(self, choices, tag_specs):
        """Determine current (default) setting of tag by looking into tag_specs (e.g. [ "snmp", "!tcp", "test" ] )"""
        default_tag = None
        ignore = True
        for t in tag_specs:
            if t[0] == '!':
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

    def _tag_condition_dropdown(self, varprefix, tagtype, deflt, id_):
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
            div_is_open = html.request.var(dropdown_id, "ignore") != "ignore"
        else:
            div_is_open = deflt != "ignore"
        html.open_div(id_="%stag_sel_%s" % (varprefix, id_),
                      style="display: none;" if not div_is_open else None)


class LabelCondition(Transform):
    def __init__(self, title, help_txt):
        super(LabelCondition, self).__init__(
            ListOf(
                Tuple(
                    orientation="horizontal",
                    elements=[
                        DropdownChoice(choices=[
                            ("is", _("has")),
                            ("is_not", _("has not")),
                        ],),
                        SingleLabel(world=Labels.World.CONFIG,),
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
                    operator, label_value)
        return label_conditions

    def _single_label_from_valuespec(self, operator, label_value):
        if operator == "is":
            return label_value
        if operator == "is_not":
            return {"$ne": label_value}
        raise NotImplementedError()


@page_registry.register_page("ajax_dict_host_tag_condition_get_choice")
class PageAjaxDictHostTagConditionGetChoice(ABCPageListOfMultipleGetChoice):
    def _get_choices(self, request):
        condition = DictHostTagCondition("Dummy title", "Dummy help")
        return condition._get_tag_group_choices()


def transform_simple_to_multi_host_rule_match_conditions(value):
    if value and "match_folder" in value:
        value["match_folders"] = [value.pop("match_folder")]
    return value


def _simple_host_rule_match_conditions():
    return [_site_rule_match_condition(),
            _single_folder_rule_match_condition()] + _common_host_rule_match_conditions()


def multifolder_host_rule_match_conditions():
    return [_site_rule_match_condition(),
            _multi_folder_rule_match_condition()] + _common_host_rule_match_conditions()


def _site_rule_match_condition():
    return (
        "match_site",
        DualListChoice(
            title=_("Match site"),
            help=_("This condition makes the rule match only hosts of "
                   "the selected sites."),
            choices=config.site_attribute_choices,
        ),
    )


def _multi_folder_rule_match_condition():
    return (
        "match_folders",
        ListOf(FullPathFolderChoice(
            title=_("Folder"),
            help=_("This condition makes the rule match only hosts that are managed "
                   "via WATO and that are contained in this folder - either directly "
                   "or in one of its subfolders."),
        ),
               add_label=_("Add additional folder"),
               title=_("Match folders"),
               movable=False),
    )


def _common_host_rule_match_conditions():
    return [
        ("match_hosttags", HostTagCondition(title=_("Match Host Tags"))),
        ("match_hostlabels",
         Labels(
             Labels.World.CORE,
             title=_("Match Host Labels"),
             help=_("Use this condition to select hosts based on the configured host labels."),
         )),
        ("match_hostgroups",
         HostGroupChoice(
             title=_("Match Host Groups"),
             help=_("The host must be in one of the selected host groups"),
             allow_empty=False,
         )),
        ("match_hosts",
         ListOfStrings(
             valuespec=MonitoredHostname(),
             title=_("Match only the following hosts"),
             size=24,
             orientation="horizontal",
             allow_empty=False,
             empty_text=
             _("Please specify at least one host. Disable the option if you want to allow all hosts."
              ),
         )),
        ("match_exclude_hosts",
         ListOfStrings(
             valuespec=MonitoredHostname(),
             title=_("Exclude the following hosts"),
             size=24,
             orientation="horizontal",
         ))
    ]


def _single_folder_rule_match_condition():
    return (
        "match_folder",
        FolderChoice(
            title=_("Match folder"),
            help=_("This condition makes the rule match only hosts that are managed "
                   "via WATO and that are contained in this folder - either directly "
                   "or in one of its subfolders."),
        ),
    )


def get_search_expression():
    search = html.request.get_unicode_input("search")
    if search is not None:
        search = search.strip().lower()
    return search


def get_hostnames_from_checkboxes(filterfunc: _Optional[Callable] = None,
                                  deflt: bool = False) -> List[str]:
    """Create list of all host names that are select with checkboxes in the current file.
    This is needed for bulk operations."""
    selected = config.user.get_rowselection(weblib.selection_id(),
                                            'wato-folder-/' + watolib.Folder.current().path())
    search_text = html.request.var("search")

    selected_host_names = []
    for host_name, host in sorted(watolib.Folder.current().hosts().items()):
        if ((not search_text or (search_text.lower() in host_name.lower())) and
            ('_c_' + host_name) in selected):
            if filterfunc is None or filterfunc(host):
                selected_host_names.append(host_name)
    return selected_host_names


def get_hosts_from_checkboxes(filterfunc=None):
    """Create list of all host objects that are select with checkboxes in the current file.
    This is needed for bulk operations."""
    folder = watolib.Folder.current()
    return [folder.host(host_name) for host_name in get_hostnames_from_checkboxes(filterfunc)]


class FullPathFolderChoice(DropdownChoice):
    def __init__(self, **kwargs):
        kwargs["choices"] = watolib.Folder.folder_choices_fulltitle
        kwargs.setdefault("title", _("Folder"))
        DropdownChoice.__init__(self, **kwargs)


class FolderChoice(DropdownChoice):
    def __init__(self, **kwargs):
        kwargs["choices"] = watolib.Folder.folder_choices
        kwargs.setdefault("title", _("Folder"))
        DropdownChoice.__init__(self, **kwargs)


def get_check_information():
    if 'automation_get_check_information' not in g:
        g.automation_get_check_information = watolib.check_mk_local_automation(
            "get-check-information")

    return g.automation_get_check_information


def get_section_information():
    if 'automation_get_section_information' not in g:
        g.automation_get_section_information = watolib.check_mk_local_automation(
            "get-section-information")

    return g.automation_get_section_information
