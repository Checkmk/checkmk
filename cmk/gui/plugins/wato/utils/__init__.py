#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""Module to hold shared code for WATO internals and the WATO plugins"""

# TODO: More feature related splitting up would be better

import os
import abc
import json
import subprocess

import six

import cmk.utils.plugin_registry

import cmk.gui.config as config
import cmk.gui.userdb as userdb
import cmk.gui.backup as backup
from cmk.gui.i18n import _u, _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
from cmk.gui.exceptions import MKUserError, MKGeneralException
from cmk.gui.valuespec import (
    TextAscii,
    Dictionary,
    RadioChoice,
    Tuple,
    Checkbox,
    Integer,
    DropdownChoice,
    Alternative,
    Password,
    Transform,
    FixedValue,
    ListOf,
    RegExpUnicode,
    RegExp,
    TextUnicode,
    ElementSelection,
    OptionalDropdownChoice,
    Percentage,
    Float,
    CascadingDropdown,
    ListChoice,
    ListOfStrings,
    DualListChoice,
    ValueSpec,
    Url,
)
from cmk.gui.plugins.wato.utils.base_modes import (
    WatoMode,
    WatoWebApiMode,
)
from cmk.gui.plugins.wato.utils.simple_modes import (
    SimpleModeType,
    SimpleListMode,
    SimpleEditMode,
)
from cmk.gui.plugins.wato.utils.context_buttons import (
    global_buttons,
    changelog_button,
    home_button,
    host_status_button,
)
from cmk.gui.plugins.wato.utils.html_elements import (
    wato_styles,
    wato_confirm,
    search_form,
)
from cmk.gui.plugins.wato.utils.main_menu import (
    MainMenu,
    MenuItem,
    main_module_registry,
    MainModule,
    WatoModule,
    register_modules,
)
import cmk.gui.watolib as watolib
from cmk.gui.watolib.timeperiods import TimeperiodSelection
from cmk.gui.watolib import (
    service_levels,
    get_search_expression,
    multisite_dir,
    wato_root_dir,
    user_script_title,
    user_script_choices,
    is_wato_slave_site,
    wato_fileheader,
    add_change,
    log_audit,
    site_neutral_path,
    register_hook,
    rulespec_group_registry,
    RulespecGroup,
    RulespecSubGroup,
    get_rulegroup,
    register_rule,
    declare_host_attribute,
    register_notification_parameters,
    add_replication_paths,
    make_action_link,
    folder_preserving_link,
    ContactGroupsAttribute,
    NagiosTextAttribute,
    NagiosValueSpecAttribute,
    ValueSpecAttribute,
    ACTestCategories,
    ACTest,
    ac_test_registry,
    ACResultCRIT,
    ACResultWARN,
    ACResultOK,
    config_domain_registry,
    ConfigDomain,
    ConfigDomainCore,
    ConfigDomainOMD,
    ConfigDomainEventConsole,
    ConfigDomainGUI,
    ConfigDomainCACertificates,
    LivestatusViaTCP,
    WatoBackgroundJob,
    UserSelection,
    multifolder_host_rule_match_conditions,
    simple_host_rule_match_conditions,
    transform_simple_to_multi_host_rule_match_conditions,
    rule_option_elements,
    ConfigHostname,
)
from cmk.gui.plugins.watolib.utils import (
    config_variable_group_registry,
    ConfigVariableGroup,
    config_variable_registry,
    ConfigVariable,
    register_configvar,
)
import cmk.gui.forms as forms
from cmk.gui.permissions import (
    permission_section_registry,
    PermissionSection,
)


@permission_section_registry.register
class PermissionSectionWATO(PermissionSection):
    @property
    def name(self):
        return "wato"

    @property
    def title(self):
        return _("WATO - Check_MK's Web Administration Tool")


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


def vs_bulk_discovery(render_form=False, include_subfolders=True):
    if render_form:
        render = "form"
    else:
        render = None

    if include_subfolders:
        selection_elements = [Checkbox(label=_("Include all subfolders"), default_value=True)]
    else:
        selection_elements = []

    selection_elements += [
        Checkbox(
            label=_("Only include hosts that failed on previous discovery"), default_value=False),
        Checkbox(label=_("Only include hosts with a failed discovery check"), default_value=False),
        Checkbox(label=_("Exclude hosts where the agent is unreachable"), default_value=False),
    ]

    return Dictionary(
        title=_("Bulk discovery"),
        render=render,
        elements=[
            ("mode",
             RadioChoice(
                 title=_("Mode"),
                 orientation="vertical",
                 default_value="new",
                 choices=[
                     ("new", _("Add unmonitored services")),
                     ("remove", _("Remove vanished services")),
                     ("fixall", _("Add unmonitored & remove vanished services")),
                     ("refresh", _("Refresh all services (tabula rasa)")),
                 ],
             )),
            ("selection", Tuple(title=_("Selection"), elements=selection_elements)),
            ("performance",
             Tuple(
                 title=_("Performance options"),
                 elements=[
                     Checkbox(label=_("Use cached data if present"), default_value=True),
                     Checkbox(label=_("Do full SNMP scan for SNMP devices"), default_value=True),
                     Integer(label=_("Number of hosts to handle at once"), default_value=10),
                 ])),
            ("error_handling",
             Checkbox(
                 title=_("Error handling"),
                 label=_("Ignore errors in single check plugins"),
                 default_value=True)),
        ],
        optional_keys=[],
    )


class UserIconOrAction(DropdownChoice):
    def __init__(self, **kwargs):
        empty_text = _("In order to be able to choose actions here, you need to "
                       "<a href=\"%s\">define your own actions</a>.") % \
                          "wato.py?mode=edit_configvar&varname=user_icons_and_actions"

        kwargs.update({
            'choices': self.list_user_icons_and_actions,
            'allow_empty': False,
            'empty_text': empty_text,
            'help': kwargs.get('help', '') + ' ' + empty_text,
        })
        super(UserIconOrAction, self).__init__(**kwargs)

    def list_user_icons_and_actions(self):
        choices = []
        for key, action in config.user_icons_and_actions.items():
            label = key
            if 'title' in action:
                label += ' - ' + action['title']
            if 'url' in action:
                label += ' (' + action['url'][0] + ')'

            choices.append((key, label))
        return sorted(choices, key=lambda x: x[1])


class SNMPCredentials(Alternative):
    def __init__(self, allow_none=False, **kwargs):
        def alternative_match(x):
            if kwargs.get("only_v3"):
                # NOTE: Indices are shifted by 1 due to a only_v3 hack below!!
                if x is None or len(x) == 2:
                    return 0  # noAuthNoPriv
                if len(x) == 4:
                    return 1  # authNoPriv
                if len(x) == 6:
                    return 2  # authPriv
            else:
                if x is None or isinstance(x, six.string_types):
                    return 0  # community only
                if len(x) == 1 or len(x) == 2:
                    return 1  # noAuthNoPriv
                if len(x) == 4:
                    return 2  # authNoPriv
                if len(x) == 6:
                    return 3  # authPriv
            raise MKGeneralException("invalid SNMP credential format %s" % x)

        if allow_none:
            none_elements = [FixedValue(
                None,
                title=_("No explicit credentials"),
                totext="",
            )]

            # Wrap match() function defined above
            match = lambda x: 0 if x is None else (alternative_match(x) + 1)
        else:
            none_elements = []
            match = alternative_match

        kwargs.update({
            "elements": none_elements + [
                Password(
                    title=_("SNMP community (SNMP Versions 1 and 2c)"),
                    allow_empty=False,
                ),
                Transform(
                    Tuple(
                        title=
                        _("Credentials for SNMPv3 without authentication and privacy (noAuthNoPriv)"
                         ),
                        elements=[
                            FixedValue(
                                "noAuthNoPriv",
                                title=_("Security Level"),
                                totext=_("No authentication, no privacy"),
                            ),
                            TextAscii(title=_("Security name"), attrencode=True, allow_empty=False),
                        ]),
                    forth=lambda x: x if (x and len(x) == 2) else ("noAuthNoPriv", "")),
                Tuple(
                    title=_(
                        "Credentials for SNMPv3 with authentication but without privacy (authNoPriv)"
                    ),
                    elements=[
                        FixedValue(
                            "authNoPriv",
                            title=_("Security Level"),
                            totext=_("authentication but no privacy"),
                        ),
                    ] + self._snmpv3_auth_elements()),
                Tuple(
                    title=_("Credentials for SNMPv3 with authentication and privacy (authPriv)"),
                    elements=[
                        FixedValue(
                            "authPriv",
                            title=_("Security Level"),
                            totext=_("authentication and encryption"),
                        ),
                    ] + self._snmpv3_auth_elements() + [
                        DropdownChoice(
                            choices=[
                                ("DES", _("DES")),
                                ("AES", _("AES")),
                            ],
                            title=_("Privacy protocol")),
                        Password(
                            title=_("Privacy pass phrase"),
                            minlen=8,
                        ),
                    ]),
            ],
            "match": match,
            "style": "dropdown",
        })
        if "default_value" not in kwargs:
            kwargs["default_value"] = "public"

        if kwargs.get("only_v3"):
            # HACK: This shifts the indices in alternative_match above!!
            # Furthermore, it doesn't work in conjunction with allow_none.
            kwargs["elements"].pop(0)
            kwargs.setdefault("title", _("SNMPv3 credentials"))
        else:
            kwargs.setdefault("title", _("SNMP credentials"))
        kwargs["orientation"] = "vertical"
        super(SNMPCredentials, self).__init__(**kwargs)

    def _snmpv3_auth_elements(self):
        return [
            DropdownChoice(
                choices=[
                    ("md5", _("MD5")),
                    ("sha", _("SHA1")),
                ],
                title=_("Authentication protocol")),
            TextAscii(title=_("Security name"), attrencode=True),
            Password(
                title=_("Authentication password"),
                minlen=8,
            )
        ]


class IPMIParameters(Dictionary):
    def __init__(self, **kwargs):
        kwargs["title"] = _("IPMI credentials")
        kwargs["elements"] = [
            ("username", TextAscii(
                title=_("Username"),
                allow_empty=False,
            )),
            ("password", Password(
                title=_("Password"),
                allow_empty=False,
            )),
        ]
        kwargs["optional_keys"] = []
        super(IPMIParameters, self).__init__(**kwargs)


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
         DropdownChoice(
             title=_("Case translation"),
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


class GroupSelection(ElementSelection):
    def __init__(self, what, **kwargs):
        kwargs.setdefault(
            'empty_text',
            _('You have not defined any %s group yet. Please '
              '<a href="wato.py?mode=edit_%s_group">create</a> at least one first.') % (what, what))
        super(GroupSelection, self).__init__(**kwargs)
        self._what = what
        # Allow to have "none" entry with the following title
        self._no_selection = kwargs.get("no_selection")

    def get_elements(self):
        all_groups = userdb.load_group_information()
        this_group = all_groups.get(self._what, {})
        # replace the title with the key if the title is empty
        elements = [(k, t['alias'] if t['alias'] else k) for (k, t) in this_group.items()]
        if self._no_selection:
            # Beware: ElementSelection currently can only handle string
            # keys, so we cannot take 'None' as a value.
            elements.append(('', self._no_selection))
        return dict(elements)


def passwordstore_choices():
    store = watolib.PasswordStore()
    return [(ident, pw["title"])
            for ident, pw in store.filter_usable_entries(store.load_for_reading()).items()]


class PasswordFromStore(CascadingDropdown):
    def __init__(self, *args, **kwargs):
        kwargs["choices"] = [
            ("password", _("Password"), Password(allow_empty=kwargs.get("allow_empty", True),)),
            ("store", _("Stored password"),
             DropdownChoice(
                 choices=passwordstore_choices,
                 sorted=True,
                 invalid_choice="complain",
                 invalid_choice_title=_("Password does not exist or using not permitted"),
                 invalid_choice_error=_("The configured password has either be removed or you "
                                        "are not permitted to use this password. Please choose "
                                        "another one."),
             )),
        ]
        kwargs["orientation"] = "horizontal"

        CascadingDropdown.__init__(self, *args, **kwargs)


def IndividualOrStoredPassword(*args, **kwargs):
    return Transform(
        PasswordFromStore(*args, **kwargs),
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
                   "Have a look at the python requests module documentation for further information."
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
    """Special version of register_rule, dedicated to checks."""
    if valuespec and isinstance(valuespec, Dictionary) and match_type != "dict":
        raise MKGeneralException(
            "Check parameter definition for %s has type Dictionary, but match_type %s" %
            (checkgroup, match_type))

    # Added during 1.6 development for easier transition. Convert all legacy subgroup
    # parameters (which are either str/unicode to group classes
    if isinstance(subgroup, six.string_types):
        subgroup = get_rulegroup("checkparams/" + subgroup).__class__

    # Enclose this valuespec with a TimeperiodValuespec
    # The given valuespec will be transformed to a list of valuespecs,
    # whereas each element can be set to a specific timeperiod
    if valuespec:
        valuespec = TimeperiodValuespec(valuespec)

    # Register rule for discovered checks
    if valuespec and has_inventory:  # would be useless rule if check has no parameters
        itemenum = None
        if itemspec:
            itemtype = "item"
            itemname = itemspec.title()
            itemhelp = itemspec.help()
            if isinstance(itemspec, (DropdownChoice, OptionalDropdownChoice)):
                itemenum = itemspec._choices
        else:
            itemtype = None
            itemname = None
            itemhelp = None

        register_rule(
            subgroup,
            varname="checkgroup_parameters:%s" % checkgroup,
            title=title,
            valuespec=valuespec,
            itemspec=itemspec,
            itemtype=itemtype,
            itemname=itemname,
            itemhelp=itemhelp,
            itemenum=itemenum,
            match=match_type,
            deprecated=deprecated)

    if register_static_check:
        # Register rule for static checks
        elements = [
            CheckTypeGroupSelection(
                checkgroup,
                title=_("Checktype"),
                help=_("Please choose the check plugin"),
            )
        ]
        if itemspec:
            elements.append(itemspec)
        else:
            # In case of static checks without check-item, add the fixed
            # valuespec to add "None" as second element in the tuple
            elements.append(FixedValue(
                None,
                totext='',
            ))
        if not valuespec:
            valuespec =\
                FixedValue(None,
                    help = _("This check has no parameters."),
                    totext = "")

        if not valuespec.title():
            valuespec._title = _("Parameters")

        elements.append(valuespec)

        # There is never a RulespecSubGroup declaration for the static checks.
        # Create some based on the regular check groups which should have a definition
        main_group_static_class = rulespec_group_registry["static"]
        checkparams_static_sub_group_class = type("%sStatic" % subgroup.__name__, (subgroup,), {
            "main_group": main_group_static_class,
        })
        rulespec_group_registry.register(checkparams_static_sub_group_class)

        register_rule(
            checkparams_static_sub_group_class,
            "static_checks:%s" % checkgroup,
            title=title,
            valuespec=Tuple(
                title=valuespec.title(),
                elements=elements,
            ),
            itemspec=itemspec,
            match="all",
            deprecated=deprecated)


@rulespec_group_registry.register
class RulespecGroupDiscoveryCheckParameters(RulespecGroup):
    @property
    def name(self):
        return "checkparams"

    @property
    def title(self):
        return _("Parameters for discovered services")

    @property
    def help(self):
        return _("Levels and other parameters for checks found by the Check_MK service discovery.\n"
                 "Use these rules in order to define parameters like filesystem levels, "
                 "levels for CPU load and other things for services that have been found "
                 "by the automatic service discovery of Check_MK.")


group = RulespecGroupDiscoveryCheckParameters().name


@rulespec_group_registry.register
class RulespecGroupCheckParametersNetworking(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupDiscoveryCheckParameters

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
        return RulespecGroupDiscoveryCheckParameters

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
        return RulespecGroupDiscoveryCheckParameters

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
        return RulespecGroupDiscoveryCheckParameters

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
        return RulespecGroupDiscoveryCheckParameters

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
        return RulespecGroupDiscoveryCheckParameters

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
        return RulespecGroupDiscoveryCheckParameters

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
        return RulespecGroupDiscoveryCheckParameters

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
        return _("Discovery - automatic service detection")


class TimeperiodValuespec(ValueSpec):
    # Used by GUI switch
    # The actual set mode
    # "0" - no timespecific settings
    # "1" - timespecific settings active
    tp_toggle_var = "tp_toggle"
    tp_current_mode = "tp_active"

    tp_default_value_key = "tp_default_value"  # Used in valuespec
    tp_values_key = "tp_values"  # Used in valuespec

    def __init__(self, valuespec):
        super(TimeperiodValuespec, self).__init__(
            title=valuespec.title(),
            help=valuespec.help(),
        )
        self._enclosed_valuespec = valuespec

    def default_value(self):
        # If nothing is configured, simply return the default value of the enclosed valuespec
        return self._enclosed_valuespec.default_value()

    def render_input(self, varprefix, value):
        # The display mode differs when the valuespec is activated
        vars_copy = dict(html.request.itervars())

        # The timeperiod mode can be set by either the GUI switch or by the value itself
        # GUI switch overrules the information stored in the value
        if html.request.has_var(self.tp_toggle_var):
            is_active = self._is_switched_on()
        else:
            is_active = self.is_active(value)

        # Set the actual used mode
        html.hidden_field(self.tp_current_mode, "%d" % is_active)

        mode = _("Disable") if is_active else _("Enable")
        vars_copy[self.tp_toggle_var] = "%d" % (not is_active)
        toggle_url = html.makeuri(vars_copy.items())

        if is_active:
            value = self._get_timeperiod_value(value)
            self._get_timeperiod_valuespec().render_input(varprefix, value)
            html.buttonlink(
                toggle_url,
                _("%s timespecific parameters") % mode,
                class_=["toggle_timespecific_parameter"])
        else:
            value = self._get_timeless_value(value)
            r = self._enclosed_valuespec.render_input(varprefix, value)
            html.buttonlink(
                toggle_url,
                _("%s timespecific parameters") % mode,
                class_=["toggle_timespecific_parameter"])
            return r

    def value_to_text(self, value):
        text = ""
        if self.is_active(value):
            # TODO/Phantasm: highlight currently active timewindow
            text += self._get_timeperiod_valuespec().value_to_text(value)
        else:
            text += self._enclosed_valuespec.value_to_text(value)
        return text

    def from_html_vars(self, varprefix):
        if html.request.var(self.tp_current_mode) == "1":
            # Fetch the timespecific settings
            parameters = self._get_timeperiod_valuespec().from_html_vars(varprefix)
            if parameters[self.tp_values_key]:
                return parameters

            # Fall back to enclosed valuespec data when no timeperiod is set
            return parameters[self.tp_default_value_key]

        # Fetch the data from the enclosed valuespec
        return self._enclosed_valuespec.from_html_vars(varprefix)

    def canonical_value(self):
        return self._enclosed_valuespec.canonical_value()

    def validate_datatype(self, value, varprefix):
        if self.is_active(value):
            self._get_timeperiod_valuespec().validate_datatype(value, varprefix)
        else:
            self._enclosed_valuespec.validate_datatype(value, varprefix)

    def validate_value(self, value, varprefix):
        if self.is_active(value):
            self._get_timeperiod_valuespec().validate_value(value, varprefix)
        else:
            self._enclosed_valuespec.validate_value(value, varprefix)

    def _get_timeperiod_valuespec(self):
        return Dictionary(
            elements=[
                (self.tp_default_value_key,
                 Transform(
                     self._enclosed_valuespec,
                     title=_("Default parameters when no timeperiod matches"))),
                (self.tp_values_key,
                 ListOf(
                     Tuple(elements=[
                         watolib.timeperiods.TimeperiodSelection(
                             title=_("Match only during timeperiod"),
                             help=_("Match this rule only during times where the "
                                    "selected timeperiod from the monitoring "
                                    "system is active."),
                         ), self._enclosed_valuespec
                     ]),
                     title=_("Configured timeperiod parameters"),
                 )),
            ],
            optional_keys=False,
        )

    # Checks whether the tp-mode is switched on through the gui
    def _is_switched_on(self):
        return html.request.var(self.tp_toggle_var) == "1"

    # Checks whether the value itself already uses the tp-mode
    def is_active(self, value):
        return isinstance(value, dict) and self.tp_default_value_key in value

    # Returns simply the value or converts a plain value to a tp-value
    def _get_timeperiod_value(self, value):
        if isinstance(value, dict) and self.tp_default_value_key in value:
            return value
        return {self.tp_values_key: [], self.tp_default_value_key: value}

    # Returns simply the value or converts tp-value back to a plain value
    def _get_timeless_value(self, value):
        if isinstance(value, dict) and self.tp_default_value_key in value:
            return value.get(self.tp_default_value_key)
        return value


class CheckTypeGroupSelection(ElementSelection):
    def __init__(self, checkgroup, **kwargs):
        super(CheckTypeGroupSelection, self).__init__(**kwargs)
        self._checkgroup = checkgroup

    def get_elements(self):
        checks = watolib.check_mk_local_automation("get-check-information")
        elements = dict([(cn, "%s - %s" % (cn, c["title"]))
                         for (cn, c) in checks.items()
                         if c.get("group") == self._checkgroup])
        return elements

    def value_to_text(self, value):
        return "<tt>%s</tt>" % value


# The following function looks like a value spec and in fact
# can be used like one (but take no parameters)
def PredictiveLevels(**args):
    dif = args.get("default_difference", (2.0, 4.0))
    unitname = args.get("unit", "")
    if unitname:
        unitname += " "

    return Dictionary(
        title=_("Predictive Levels"),
        optional_keys=[
            "weight", "levels_upper", "levels_upper_min", "levels_lower", "levels_lower_max"
        ],
        default_keys=["levels_upper"],
        columns=1,
        headers="sup",
        elements=[
            ("period",
             DropdownChoice(
                 title=_("Base prediction on"),
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
                          Float(
                              title=_("Warning at"),
                              unit=unitname + _("above predicted value"),
                              default_value=dif[0]),
                          Float(
                              title=_("Critical at"),
                              unit=unitname + _("above predicted value"),
                              default_value=dif[1]),
                      ])),
                     ("relative", _("Relative difference from prediction"),
                      Tuple(elements=[
                          Percentage(
                              title=_("Warning at"),
                              unit=_("% above predicted value"),
                              default_value=10),
                          Percentage(
                              title=_("Critical at"),
                              unit=_("% above predicted value"),
                              default_value=20),
                      ])),
                     ("stdev", _("In relation to standard deviation"),
                      Tuple(elements=[
                          Float(
                              title=_("Warning at"),
                              unit=_("times the standard deviation above the predicted value"),
                              default_value=2.0),
                          Float(
                              title=_("Critical at"),
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
                          Float(
                              title=_("Warning at"),
                              unit=unitname + _("below predicted value"),
                              default_value=2.0),
                          Float(
                              title=_("Critical at"),
                              unit=unitname + _("below predicted value"),
                              default_value=4.0),
                      ])),
                     ("relative", _("Relative difference from prediction"),
                      Tuple(elements=[
                          Percentage(
                              title=_("Warning at"),
                              unit=_("% below predicted value"),
                              default_value=10),
                          Percentage(
                              title=_("Critical at"),
                              unit=_("% below predicted value"),
                              default_value=20),
                      ])),
                     ("stdev", _("In relation to standard deviation"),
                      Tuple(elements=[
                          Float(
                              title=_("Warning at"),
                              unit=_("times the standard deviation below the predicted value"),
                              default_value=2.0),
                          Float(
                              title=_("Critical at"),
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
        elif isinstance(v, tuple) and v != (None, None):
            return 1
        return 0

    help_txt = kwargs.get("help")
    unit = kwargs.get("unit")
    title = kwargs.get("title")
    default_levels = kwargs.get("default_levels", (0.0, 0.0))
    default_difference = kwargs.get("default_difference", (0, 0))
    if "default_value" in kwargs:
        default_value = kwargs["default_value"]
    else:
        default_value = default_levels if default_levels else None

    return Alternative(
        title=title,
        help=help_txt,
        show_titles=False,
        style="dropdown",
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
                        allow_int=True),
                    Float(
                        unit=unit,
                        title=_("Critical at"),
                        default_value=default_levels[1],
                        allow_int=True),
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
    elif varname in ["custom_checks", "datasource_programs"]:
        return config.user.may("wato.rulesets") and config.user.may(
            "wato.add_or_modify_executables")
    elif varname == "agent_config:custom_files":
        return config.user.may("wato.rulesets") and config.user.may(
            "wato.agent_deploy_custom_files")
    return config.user.may("wato.rulesets")


class CheckTypeSelection(DualListChoice):
    def __init__(self, **kwargs):
        super(CheckTypeSelection, self).__init__(rows=25, **kwargs)

    def get_elements(self):
        checks = watolib.check_mk_local_automation("get-check-information")
        elements = [(cn, (cn + " - " + c["title"])[:60]) for (cn, c) in checks.items()]
        elements.sort()
        return elements


class EventsMode(WatoMode):
    __metaclass__ = abc.ABCMeta

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
           ( "match_host_event",
              ListChoice(
                   title = _("Match host event type"),
                   help = _("Select the host event types and transitions this rule should handle.<br>"
                            "Note: If you activate this option and do <b>not</b> also specify service event "
                            "types then this rule will never hold for service notifications!<br>"
                            "Note: You can only match on event types <a href=\"%s\">created by the core</a>.") % \
                                "wato.py?mode=edit_ruleset&varname=extra_host_conf%3Anotification_options",
                   choices = [
                       ( 'rd', _("UP")          + u" ➤ " + _("DOWN")),
                       ( 'ru', _("UP")          + u" ➤ " + _("UNREACHABLE")),

                       ( 'dr', _("DOWN")        + u" ➤ " + _("UP")),
                       ( 'du', _("DOWN")        + u" ➤ " + _("UNREACHABLE")),

                       ( 'ud', _("UNREACHABLE") + u" ➤ " + _("DOWN")),
                       ( 'ur', _("UNREACHABLE") + u" ➤ " + _("UP")),

                       ( '?r', _("any")         + u" ➤ " + _("UP")),
                       ( '?d', _("any")         + u" ➤ " + _("DOWN")),
                       ( '?u', _("any")         + u" ➤ " + _("UNREACHABLE")),
                   ] + add_choices,
                   default_value = [ 'rd', 'dr', ] + add_default,
             )
           ),
           ( "match_service_event",
               ListChoice(
                   title = _("Match service event type"),
                    help  = _("Select the service event types and transitions this rule should handle.<br>"
                              "Note: If you activate this option and do <b>not</b> also specify host event "
                              "types then this rule will never hold for host notifications!<br>"
                              "Note: You can only match on event types <a href=\"%s\">created by the core</a>.") % \
                                "wato.py?mode=edit_ruleset&varname=extra_service_conf%3Anotification_options",
                   choices = [
                       ( 'rw', _("OK")      + u" ➤ " + _("WARN")),
                       ( 'rr', _("OK")      + u" ➤ " + _("OK")),

                       ( 'rc', _("OK")      + u" ➤ " + _("CRIT")),
                       ( 'ru', _("OK")      + u" ➤ " + _("UNKNOWN")),

                       ( 'wr', _("WARN")    + u" ➤ " + _("OK")),
                       ( 'wc', _("WARN")    + u" ➤ " + _("CRIT")),
                       ( 'wu', _("WARN")    + u" ➤ " + _("UNKNOWN")),

                       ( 'cr', _("CRIT")    + u" ➤ " + _("OK")),
                       ( 'cw', _("CRIT")    + u" ➤ " + _("WARN")),
                       ( 'cu', _("CRIT")    + u" ➤ " + _("UNKNOWN")),

                       ( 'ur', _("UNKNOWN") + u" ➤ " + _("OK")),
                       ( 'uw', _("UNKNOWN") + u" ➤ " + _("WARN")),
                       ( 'uc', _("UNKNOWN") + u" ➤ " + _("CRIT")),

                       ( '?r', _("any") + u" ➤ " + _("OK")),
                       ( '?w', _("any") + u" ➤ " + _("WARN")),
                       ( '?c', _("any") + u" ➤ " + _("CRIT")),
                       ( '?u', _("any") + u" ➤ " + _("UNKNOWN")),

                   ] + add_choices,
                   default_value = [ 'rw', 'rc', 'ru', 'wc', 'wu', 'uc', ] + add_default,
              )
            ),
        ]

    @classmethod
    def _generic_rule_match_conditions(cls):
        return simple_host_rule_match_conditions() + [
            ( "match_servicegroups",
              userdb.GroupChoice("service",
                  title = _("Match Service Groups"),
                  help = _("The service must be in one of the selected service groups. For host events this condition "
                           "never matches as soon as at least one group is selected."),
                  allow_empty = False,
              )
            ),
            ( "match_exclude_servicegroups",
              userdb.GroupChoice("service",
                  title = _("Exclude Service Groups"),
                  help = _("The service must not be in one of the selected service groups. For host events this condition "
                           "is simply ignored."),
                  allow_empty = False,
              )
            ),
            ( "match_servicegroups_regex",
              Tuple(
                    title = _("Match Service Groups (regex)"),
                    elements = [
                    DropdownChoice(
                        choices = [
                            ( "match_id",    _("Match the internal identifier")),
                            ( "match_alias", _("Match the alias"))
                        ],
                        default = "match_id"
                      ),
                      ListOfStrings(
                          help = _("The service group alias must match one of the following regular expressions."
                                   " For host events this condition never matches as soon as at least one group is selected."),
                          valuespec = RegExpUnicode(
                              size = 32,
                              mode = RegExpUnicode.infix,
                          ),
                          orientation = "horizontal",
                      )
                    ]
              )
            ),
            ( "match_exclude_servicegroups_regex",
              Tuple(
                    title = _("Exclude Service Groups (regex)"),
                    elements = [
                      DropdownChoice(
                        choices = [
                            ( "match_id",    _("Match the internal identifier")),
                            ( "match_alias", _("Match the alias"))
                        ],
                        default = "match_id"
                      ),
                      ListOfStrings(
                          help = _("The service group alias must not match one of the following regular expressions. "
                                   "For host events this condition is simply ignored."),
                          valuespec = RegExpUnicode(
                              size = 32,
                              mode = RegExpUnicode.infix,
                          ),
                          orientation = "horizontal",
                      )
                    ]
              )
            ),
            ( "match_services",
              ListOfStrings(
                  title = _("Match only the following services"),
                  help = _("Specify a list of regular expressions that must match the <b>beginning</b> of the "
                           "service name in order for the rule to match. Note: Host notifications never match this "
                           "rule if this option is being used."),
                  valuespec = RegExpUnicode(
                      size = 32,
                      mode = RegExpUnicode.prefix,
                  ),
                  orientation = "horizontal",
                  allow_empty = False,
                  empty_text = _("Please specify at least one service regex. Disable the option if you want to allow all services."),
              )
            ),
            ( "match_exclude_services",
              ListOfStrings(
                  title = _("Exclude the following services"),
                  valuespec = RegExpUnicode(
                      size = 32,
                      mode = RegExpUnicode.prefix,
                  ),
                  orientation = "horizontal",
              )
            ),
            ( "match_checktype",
              CheckTypeSelection(
                  title = _("Match the following check types"),
                  help = _("Only apply the rule if the notification originates from certain types of check plugins. "
                           "Note: Host notifications never match this rule if this option is being used."),
              )
            ),
            ( "match_plugin_output",
              RegExp(
                 title = _("Match the output of the check plugin"),
                 help = _("This text is a regular expression that is being searched in the output "
                          "of the check plugins that produced the alert. It is not a prefix but an infix match."),
                 mode = RegExpUnicode.prefix,
              ),
            ),
            ( "match_contacts",
              ListOf(
                  UserSelection(only_contacts = True),
                      title = _("Match Contacts"),
                      help = _("The host/service must have one of the selected contacts."),
                      movable = False,
                      allow_empty = False,
                      add_label = _("Add contact"),
              )
            ),
            ( "match_contactgroups",
              userdb.GroupChoice("contact",
                  title = _("Match Contact Groups"),
                  help = _("The host/service must be in one of the selected contact groups. This only works with Check_MK Micro Core. " \
                           "If you don't use the CMC that filter will not apply"),
                  allow_empty = False,
              )
            ),
            ( "match_sl",
              Tuple(
                title = _("Match service level"),
                help = _("Host or service must be in the following service level to get notification"),
                orientation = "horizontal",
                show_titles = False,
                elements = [
                  DropdownChoice(label = _("from:"),  choices = service_levels, prefix_values = True),
                  DropdownChoice(label = _(" to:"),  choices = service_levels, prefix_values = True),
                ],
              ),
            ),
            ( "match_timeperiod",
              watolib.timeperiods.TimeperiodSelection(
                  title = _("Match only during timeperiod"),
                  help = _("Match this rule only during times where the selected timeperiod from the monitoring "
                           "system is active."),
                  no_preselect = True,
                  no_preselect_title = _("Select a timeperiod"),
              ),
            ),
        ]

    @abc.abstractmethod
    def _add_change(self, log_what, log_text):
        raise NotImplementedError()

    def _generic_rule_list_actions(self, rules, what, what_title, save_rules):
        if html.request.has_var("_delete"):
            nr = int(html.request.var("_delete"))
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
                from_pos = html.get_integer_input("_move")
                to_pos = html.get_integer_input("_index")
                rule = rules[from_pos]
                del rules[from_pos]  # make to_pos now match!
                rules[to_pos:to_pos] = [rule]
                save_rules(rules)
                self._add_change(what + "-move-rule",
                                 _("Changed position of %s %d") % (what_title, from_pos))


# Sort given sites argument by local, followed by slaves
# TODO: Change to sorted() mechanism
def sort_sites(sitelist):
    def custom_sort(a, b):
        return cmp(a[1].get("replication"), b[1].get("replication")) or \
               cmp(a[1].get("alias"), b[1].get("alias"))

    sitelist.sort(cmp=custom_sort)
    return sitelist


class ModeRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def plugin_base_class(self):
        return WatoMode

    def _register(self, plugin_class):
        self._entries[plugin_class.name()] = plugin_class


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
# TODO: Wow, this function REALLY has to be cleaned up
def configure_attributes(new,
                         hosts,
                         for_what,
                         parent,
                         myself=None,
                         without_attributes=None,
                         varprefix=""):
    if without_attributes is None:
        without_attributes = []

    # Collect dependency mapping for attributes (attributes that are only
    # visible, if certain host tags are set).
    dependency_mapping_tags = {}
    dependency_mapping_roles = {}
    inherited_tags = {}

    volatile_topics = []
    hide_attributes = []
    for topic, title in watolib.get_sorted_host_attribute_topics(for_what):
        topic_is_volatile = True  # assume topic is sometimes hidden due to dependencies

        if topic == _("Host tags"):
            topic_id = "wato_host_tags"
        elif topic == _("Address"):
            topic_id = "address"
        elif topic == _("Data sources"):
            topic_id = "data_sources"
        else:
            topic_id = None

        forms.header(
            title,
            isopen=topic in [None, _("Address"), _("Data sources")],
            table_id=topic_id,
        )

        for attr in watolib.get_sorted_host_attributes_by_topic(topic):
            attrname = attr.name()
            if attrname in without_attributes:
                continue  # e.g. needed to skip ipaddress in CSV-Import

            # Determine visibility information if this attribute is not always hidden
            if attr.is_visible(for_what):
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
            for host in hosts.itervalues():
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
                    host = hosts.values()[0]
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
                        inherited_from = _("Inherited from ") + html.render_a(
                            container.title(), href=url)

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

            if not new and not is_editable:
                # Bug in pylint 1.9.2 https://github.com/PyCQA/pylint/issues/1984, already fixed in master.
                if active:  # pylint: disable=simplifiable-if-statement
                    force_entry = True
                else:
                    disabled = True

            if (for_what in ["host", "cluster"] and
                    parent.locked_hosts()) or (for_what == "folder" and myself and myself.locked()):
                checkbox_code = None
            elif force_entry:
                checkbox_code = html.render_checkbox(
                    "ignored_" + checkbox_name, disabled="disabled")
                checkbox_code += html.render_hidden_field(checkbox_name, "on")
            else:
                onclick = "cmk.wato.fix_visibility(); cmk.wato.toggle_attribute(this, '%s');" % attrname
                checkbox_kwargs = {"disabled": "disabled"} if disabled else {}
                checkbox_code = html.render_checkbox(
                    checkbox_name, active, onclick=onclick, **checkbox_kwargs)

            forms.section(_u(attr.title()), checkbox=checkbox_code, section_id="attr_" + attrname)
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
                    id_="attr_entry_%s" % attrname, style="display: none;" if not active else None)
                attr.render_input(varprefix, defvalue)
                html.close_div()

                html.open_div(
                    class_="inherited",
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
                    explanation = " (" + inherited_from + ")"
                    value = inherited_value

            if for_what != "host_search" and not (for_what == "bulk" and not unique):
                _tdclass, content = attr.paint(value, "")
                if not content:
                    content = _("empty")

                if isinstance(attr, ValueSpecAttribute):
                    html.open_b()
                    html.write(content)
                    html.close_b()
                else:
                    html.b(_u(content))

            html.write_text(explanation)
            html.close_div()

        if topic_is_volatile:
            volatile_topics.append((topic or _("Basic settings")).encode('utf-8'))

    forms.end()

    dialog_properties = {
        "inherited_tags": inherited_tags,
        "check_attributes": list(
            set(dependency_mapping_tags.keys() + dependency_mapping_roles.keys() + hide_attributes)
        ),
        "aux_tags_by_tag": _get_auxtags_by_tag(),
        "depends_on_tags": dependency_mapping_tags,
        "depends_on_roles": dependency_mapping_roles,
        "volatile_topics": volatile_topics,
        "user_roles": config.user.role_ids,
        "hide_attributes": hide_attributes,
    }
    html.javascript("cmk.wato.prepare_edit_dialog(%s);"
                    "cmk.wato.fix_visibility();" % json.dumps(dialog_properties))


def _get_auxtags_by_tag():
    aux_tag_map = {}
    for entry in config.host_tag_groups():
        for tag_id, _tag_title, aux_tags in entry[2]:
            aux_tag_map[tag_id] = aux_tags
    return aux_tag_map


# Check if at least one host in a folder (or its subfolders)
# has not set a certain attribute. This is needed for the validation
# of mandatory attributes.
def some_host_hasnt_set(folder, attrname):
    # Check subfolders
    for subfolder in folder.all_subfolders().values():
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
                             stdin=open(os.devnull))
        if p.wait() != 0:
            raise MKGeneralException(_("Failed to apply the cronjob config: %s") % p.stdout.read())
