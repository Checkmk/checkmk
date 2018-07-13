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

import abc

import cmk.gui.config as config
import cmk.gui.userdb as userdb
from cmk.gui.i18n import _
from cmk.gui.htmllib import HTML
from cmk.gui.exceptions import MKUserError, MKGeneralException
from cmk.gui.valuespec import (TextAscii, Dictionary, RadioChoice, Tuple,
    Checkbox, Integer, DropdownChoice, Alternative, Password, Transform,
    FixedValue, ListOf, RegExpUnicode, RegExp, TextUnicode, ElementSelection,
    OptionalDropdownChoice, Percentage, Float,
    CascadingDropdown, ListChoice, ListOfStrings,
    DualListChoice, ValueSpec)

from cmk.gui.wato.base_modes import WatoMode
from cmk.gui.wato.context_buttons import (
    global_buttons,
    changelog_button,
    home_button,
)

from cmk.gui.wato.html_elements import (
    wato_styles,
    wato_confirm,
    search_form,
)

from cmk.gui.wato.main_menu import (
    MainMenu,
    MenuItem,
    WatoModule,
    register_modules
)

import cmk.gui.watolib as watolib
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
    configvar_order,
    site_neutral_path,
    register_configvar_group,
    register_configvar,
    register_rulegroup,
    register_rule,
    declare_host_attribute,
    register_notification_parameters,
    add_replication_paths,
    make_action_link,
    folder_preserving_link,
    ContactGroupsAttribute,
    NagiosTextAttribute,
    ValueSpecAttribute,
    ACTestCategories,
    ACTest,
    ACResultCRIT,
    ACResultWARN,
    ACResultOK,
    ConfigDomain,
    ConfigDomainCore,
    ConfigDomainOMD,
    ConfigDomainEventConsole,
    ConfigDomainGUI,
    LivestatusViaTCP,
    WatoBackgroundJob,
    UserSelection,
    TimeperiodSelection,
    multifolder_host_rule_match_conditions,
    simple_host_rule_match_conditions,
    transform_simple_to_multi_host_rule_match_conditions,
)


def rule_option_elements(disabling=True):
    elements = [
        ( "description",
          TextUnicode(
            title = _("Description"),
            help = _("A description or title of this rule"),
            size = 80,
          )
        ),
        ( "comment", watolib.RuleComment()),
        ( "docu_url",
          TextAscii(
            title = _("Documentation URL"),
            help = HTML(_("An optional URL pointing to documentation or any other page. This will be displayed "
                     "as an icon <img class=icon src='images/button_url.png'> and open a new page when clicked. "
                     "You can use either global URLs (beginning with <tt>http://</tt>), absolute local urls "
                     "(beginning with <tt>/</tt>) or relative URLs (that are relative to <tt>check_mk/</tt>).")),
            size = 80,
          ),
        ),
    ]
    if disabling:
        elements += [
            ( "disabled",
              Checkbox(
                  title = _("Rule activation"),
                  help = _("Disabled rules are kept in the configuration but are not applied."),
                  label = _("do not apply this rule"),
              )
            ),
        ]
    return elements



def PluginCommandLine():
    def _validate_custom_check_command_line(value, varprefix):
        if "--pwstore=" in value:
            raise MKUserError(varprefix, _("You are not allowed to use passwords from the password store here."))

    return TextAscii(
          title = _("Command line"),
          help = _("Please enter the complete shell command including path name and arguments to execute. "
                   "If the plugin you like to execute is located in either <tt>~/local/lib/nagios/plugins</tt> "
                   "or <tt>~/lib/nagios/plugins</tt> within your site directory, you can strip the path name and "
                   "just configure the plugin file name as command <tt>check_foobar</tt>.") + monitoring_macro_help(),
          size = "max",
          validate = _validate_custom_check_command_line,
       )


def monitoring_macro_help():
    return " " + _("You can use monitoring macros here. The most important are: "
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


def vs_bulk_discovery(render_form=False):
    if render_form:
        render = "form"
    else:
        render = None

    return Dictionary(
        title    = _("Bulk discovery"),
        render   = render,
        elements = [
            ("mode", RadioChoice(
                title       = _("Mode"),
                orientation = "vertical",
                default_value = "new",
                choices     = [
                    ("new",     _("Add unmonitored services")),
                    ("remove",  _("Remove vanished services")),
                    ("fixall",  _("Add unmonitored & remove vanished services")),
                    ("refresh", _("Refresh all services (tabula rasa)")),
                ],
            )),
            ("selection", Tuple(
                title    = _("Selection"),
                elements = [
                    Checkbox(label = _("Include all subfolders"),
                             default_value = True),
                    Checkbox(label = _("Only include hosts that failed on previous discovery"),
                             default_value = False),
                    Checkbox(label = _("Only include hosts with a failed discovery check"),
                             default_value = False),
                    Checkbox(label = _("Exclude hosts where the agent is unreachable"),
                             default_value = False),
                ]
            )),
            ("performance", Tuple(
                title    = _("Performance options"),
                elements = [
                    Checkbox(label = _("Use cached data if present"),
                             default_value = True),
                    Checkbox(label = _("Do full SNMP scan for SNMP devices"),
                             default_value = True),
                    Integer(label = _("Number of hosts to handle at once"),
                            default_value = 10),
                ]
            )),
            ("error_handling", Checkbox(
                title = _("Error handling"),
                label = _("Ignore errors in single check plugins"),
                default_value = True)),
        ],
        optional_keys = [],
    )


class UserIconOrAction(DropdownChoice):
    def __init__(self, **kwargs):
        empty_text = _("In order to be able to choose actions here, you need to "
                       "<a href=\"%s\">define your own actions</a>.") % \
                          "wato.py?mode=edit_configvar&varname=user_icons_and_actions"

        kwargs.update({
            'choices'     : self.list_user_icons_and_actions,
            'allow_empty' : False,
            'empty_text'  : empty_text,
            'help'        : kwargs.get('help', '') + ' '+empty_text,
        })
        super(UserIconOrAction, self).__init__(**kwargs)

    def list_user_icons_and_actions(self):
        choices = []
        for key, action in config.user_icons_and_actions.items():
            label = key
            if 'title' in action:
                label += ' - '+action['title']
            if 'url' in action:
                label += ' ('+action['url'][0]+')'

            choices.append((key, label))
        return sorted(choices, key = lambda x: x[1])


class SNMPCredentials(Alternative):
    def __init__(self, allow_none=False, **kwargs):
        def alternative_match(x):
            if kwargs.get("only_v3"):
                return x and (len(x) == 6 and 2 or len(x) == 4 and 1) or 0
            else:
                return type(x) == tuple and ( \
                            len(x) in [1, 2] and 1 or \
                            len(x) == 4 and 2 or 3) or 0

        if allow_none:
            none_elements = [
                FixedValue(None,
                    title = _("No explicit credentials"),
                    totext = "",
                )
            ]

            # Wrap match() function defined above
            match = lambda x: 0 if x is None else (alternative_match(x)+1)
        else:
            none_elements = []
            match = alternative_match

        kwargs.update({
            "elements": none_elements + [
                Password(
                    title = _("SNMP community (SNMP Versions 1 and 2c)"),
                    allow_empty = False,
                ),
                Transform(
                    Tuple(
                        title = _("Credentials for SNMPv3 without authentication and privacy (noAuthNoPriv)"),
                        elements = [
                            FixedValue("noAuthNoPriv",
                                title = _("Security Level"),
                                totext = _("No authentication, no privacy"),
                            ),
                            TextAscii(
                                title = _("Security name"),
                                attrencode  = True,
                                allow_empty = False
                            ),
                        ]
                    ),
                    forth = lambda x: (x and len(x) == 2) and x or ("noAuthNoPriv", "")
                ),
                Tuple(
                    title = _("Credentials for SNMPv3 with authentication but without privacy (authNoPriv)"),
                    elements = [
                        FixedValue("authNoPriv",
                            title = _("Security Level"),
                            totext = _("authentication but no privacy"),
                        ),
                    ] + self._snmpv3_auth_elements()
                ),
                Tuple(
                    title = _("Credentials for SNMPv3 with authentication and privacy (authPriv)"),
                    elements = [
                        FixedValue("authPriv",
                            title = _("Security Level"),
                            totext = _("authentication and encryption"),
                        ),
                    ] + self._snmpv3_auth_elements() + [
                        DropdownChoice(
                            choices = [
                                ( "DES", _("DES") ),
                                ( "AES", _("AES") ),
                            ],
                            title = _("Privacy protocol")
                        ),
                        Password(
                            title = _("Privacy pass phrase"),
                            minlen = 8,
                        ),
                    ]
                ),
            ],
            "match": match,
            "style": "dropdown",
        })
        if "default_value" not in kwargs:
            kwargs["default_value"] = "public"

        if kwargs.get("only_v3"):
            kwargs["elements"].pop(0)
            kwargs.setdefault("title", _("SNMPv3 credentials"))
        else:
            kwargs.setdefault("title", _("SNMP credentials"))
        kwargs["orientation"] = "vertical"
        super(SNMPCredentials, self).__init__(**kwargs)


    def _snmpv3_auth_elements(self):
        return [
            DropdownChoice(
                choices = [
                    ( "md5", _("MD5") ),
                    ( "sha", _("SHA1") ),
                ],
                title = _("Authentication protocol")
            ),
            TextAscii(
                title = _("Security name"),
                attrencode = True
            ),
            Password(
                title = _("Authentication password"),
                minlen = 8,
            )
        ]



class IPMIParameters(Dictionary):
    def __init__(self, **kwargs):
        kwargs["title"] = _("IPMI credentials")
        kwargs["elements"] = [
            ("username", TextAscii(
                  title = _("Username"),
                  allow_empty = False,
            )),
            ("password", Password(
                title = _("Password"),
                allow_empty = False,
            )),
        ]
        kwargs["optional_keys"] = []
        super(IPMIParameters, self).__init__(**kwargs)


# NOTE: When changing this keep it in sync with cmk.translations.translate_hostname()
def HostnameTranslation(**kwargs):
    help = kwargs.get("help")
    title = kwargs.get("title")
    return Dictionary(
        title = title,
        help = help,
        elements = [
            ( "drop_domain",
              FixedValue(
                  True,
                  title = _("Convert FQHN"),
                  totext = _("Drop domain part (<tt>host123.foobar.de</tt> &#8594; <tt>host123</tt>)"),
            )),
        ] + _translation_elements("host"))


def ServiceDescriptionTranslation(**kwargs):
    help = kwargs.get("help")
    title = kwargs.get("title")
    return Dictionary(
        title = title,
        help = help,
        elements = _translation_elements("service")
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
        ( "case",
          DropdownChoice(
              title = _("Case translation"),
              choices = [
                   (None,    _("Do not convert case")),
                   ("upper", _("Convert %s to upper case") % plural),
                   ("lower", _("Convert %s to lower case") % plural),
              ]
        )),
        ( "regex",
            Transform(
                ListOf(
                    Tuple(
                        orientation = "horizontal",
                        elements    =  [
                            RegExpUnicode(
                                title          = _("Regular expression"),
                                help           = _("Must contain at least one subgroup <tt>(...)</tt>"),
                                mingroups      = 0,
                                maxgroups      = 9,
                                size           = 30,
                                allow_empty    = False,
                                mode           = RegExp.prefix,
                                case_sensitive = False,
                            ),
                            TextUnicode(
                                title       = _("Replacement"),
                                help        = _("Use <tt>\\1</tt>, <tt>\\2</tt> etc. to replace matched subgroups"),
                                size        = 30,
                                allow_empty = False,
                            )
                        ],
                    ),
                    title     = _("Multiple regular expressions"),
                    help      = _("You can add any number of expressions here which are executed succesively until the first match. "
                                  "Please specify a regular expression in the first field. This expression should at "
                                  "least contain one subexpression exclosed in brackets - for example <tt>vm_(.*)_prod</tt>. "
                                  "In the second field you specify the translated %s and can refer to the first matched "
                                  "group with <tt>\\1</tt>, the second with <tt>\\2</tt> and so on, for example <tt>\\1.example.org</tt>. "
                                  "") % singular,
                    add_label = _("Add expression"),
                    movable   = False,
                ),
                forth = lambda x: type(x) == tuple and [x] or x,
            )
        ),
        ( "mapping",
          ListOf(
              Tuple(
                  orientation = "horizontal",
                  elements =  [
                      TextUnicode(
                           title = _("Original %s") % singular,
                           size = 30,
                           allow_empty = False,
                           attrencode = True,
                      ),
                      TextUnicode(
                           title = _("Translated %s") % singular,
                           size = 30,
                           allow_empty = False,
                           attrencode = True,
                      ),
                  ],
              ),
              title = _("Explicit %s mapping") % singular,
              help = _("If case conversion and regular expression do not work for all cases then you can "
                       "specify explicity pairs of origin {0} and translated {0} here. This "
                       "mapping is being applied <b>after</b> the case conversion and <b>after</b> a regular "
                       "expression conversion (if that matches).").format(singular),
              add_label = _("Add new mapping"),
              movable = False,
        )),
    ]


class GroupSelection(ElementSelection):
    def __init__(self, what, **kwargs):
        kwargs.setdefault('empty_text', _('You have not defined any %s group yet. Please '
                                          '<a href="wato.py?mode=edit_%s_group">create</a> at least one first.') %
                                                                                                    (what, what))
        super(GroupSelection, self).__init__(**kwargs)
        self._what = what
        # Allow to have "none" entry with the following title
        self._no_selection = kwargs.get("no_selection")

    def get_elements(self):
        all_groups = userdb.load_group_information()
        this_group = all_groups.get(self._what, {})
        # replace the title with the key if the title is empty
        elements = [ (k, t['alias'] if t['alias'] else k) for (k, t) in this_group.items() ]
        if self._no_selection:
            # Beware: ElementSelection currently can only handle string
            # keys, so we cannot take 'None' as a value.
            elements.append(('', self._no_selection))
        return dict(elements)



class PasswordFromStore(CascadingDropdown):
    def __init__(self, *args, **kwargs):
        kwargs["choices"] = [
            ("password", _("Password"), Password(
                allow_empty = kwargs.get("allow_empty", True),
            )),
            ("store", _("Stored password"), DropdownChoice(
                choices = self._password_choices,
                sorted = True,
                invalid_choice = "complain",
                invalid_choice_title = _("Password does not exist or using not permitted"),
                invalid_choice_error = _("The configured password has either be removed or you "
                                         "are not permitted to use this password. Please choose "
                                         "another one."),
            )),
        ]
        kwargs["orientation"] = "horizontal"

        CascadingDropdown.__init__(self, *args, **kwargs)


    def _password_choices(self):
        return [ (ident, pw["title"]) for ident, pw
                 in watolib.PasswordStore().usable_passwords().items() ]



def IndividualOrStoredPassword(*args, **kwargs):
    return Transform(
        PasswordFromStore(*args, **kwargs),
        forth = lambda v: ("password", v) if type(v) != tuple else v,
    )




def register_check_parameters(subgroup, checkgroup, title, valuespec, itemspec,
                               match_type, has_inventory=True, register_static_check=True,
                               deprecated=False):
    """Special version of register_rule, dedicated to checks."""
    if valuespec and isinstance(valuespec, Dictionary) and match_type != "dict":
        raise MKGeneralException("Check parameter definition for %s has type Dictionary, but match_type %s" %
                                 (checkgroup, match_type))

    # Enclose this valuespec with a TimeperiodValuespec
    # The given valuespec will be transformed to a list of valuespecs,
    # whereas each element can be set to a specific timeperiod
    if valuespec:
        valuespec = TimeperiodValuespec(valuespec)

    # Register rule for discovered checks
    if valuespec and has_inventory: # would be useless rule if check has no parameters
        itemenum = None
        if itemspec:
            itemtype = "item"
            itemname = itemspec.title()
            itemhelp = itemspec.help()
            if  isinstance(itemspec, (DropdownChoice, OptionalDropdownChoice)):
                itemenum = itemspec._choices
        else:
            itemtype = None
            itemname = None
            itemhelp = None

        register_rule(
            "checkparams/" + subgroup,
            varname = "checkgroup_parameters:%s" % checkgroup,
            title = title,
            valuespec = valuespec,
            itemspec = itemspec,
            itemtype = itemtype,
            itemname = itemname,
            itemhelp = itemhelp,
            itemenum = itemenum,
            match = match_type,
            deprecated = deprecated)

    if register_static_check:
        # Register rule for static checks
        elements = [
            CheckTypeGroupSelection(
                checkgroup,
                title = _("Checktype"),
                help = _("Please choose the check plugin")) ]
        if itemspec:
            elements.append(itemspec)
        else:
            # In case of static checks without check-item, add the fixed
            # valuespec to add "None" as second element in the tuple
            elements.append(FixedValue(
                None,
                totext = '',
            ))
        if not valuespec:
            valuespec =\
                FixedValue(None,
                    help = _("This check has no parameters."),
                    totext = "")

        if not valuespec.title():
            valuespec._title = _("Parameters")

        elements.append(valuespec)

        register_rule(
            "static/" + subgroup,
            "static_checks:%s" % checkgroup,
            title = title,
            valuespec = Tuple(
                title = valuespec.title(),
                elements = elements,
            ),
            itemspec = itemspec,
            match = "all",
            deprecated = deprecated)


class TimeperiodValuespec(ValueSpec):
    tp_toggle_var        = "tp_toggle"        # Used by GUI switch
    tp_current_mode      = "tp_active"        # The actual set mode
                                              # "0" - no timespecific settings
                                              # "1" - timespecific settings active

    tp_default_value_key = "tp_default_value" # Used in valuespec
    tp_values_key        = "tp_values"        # Used in valuespec


    def __init__(self, valuespec):
        super(TimeperiodValuespec, self).__init__(
            title = valuespec.title(),
            help  = valuespec.help()
        )
        self._enclosed_valuespec = valuespec


    def default_value(self):
        # If nothing is configured, simply return the default value of the enclosed valuespec
        return self._enclosed_valuespec.default_value()


    def render_input(self, varprefix, value):
        # The display mode differs when the valuespec is activated
        vars_copy = html.request.vars.copy()


        # The timeperiod mode can be set by either the GUI switch or by the value itself
        # GUI switch overrules the information stored in the value
        if html.has_var(self.tp_toggle_var):
            is_active = self._is_switched_on()
        else:
            is_active = self._is_active(value)

        # Set the actual used mode
        html.hidden_field(self.tp_current_mode, "%d" % is_active)

        mode = _("Disable") if is_active else _("Enable")
        vars_copy[self.tp_toggle_var] = "%d" % (not is_active)

        toggle_url = html.makeuri(vars_copy.items())
        html.buttonlink(toggle_url, _("%s timespecific parameters") % mode, style=["position: absolute", "right: 18px;"])

        if is_active:
            value = self._get_timeperiod_value(value)
            self._get_timeperiod_valuespec().render_input(varprefix, value)
        else:
            value = self._get_timeless_value(value)
            return self._enclosed_valuespec.render_input(varprefix, value)


    def value_to_text(self, value):
        text = ""
        if self._is_active(value):
            # TODO/Phantasm: highlight currently active timewindow
            text += self._get_timeperiod_valuespec().value_to_text(value)
        else:
            text += self._enclosed_valuespec.value_to_text(value)
        return text


    def from_html_vars(self, varprefix):
        if html.var(self.tp_current_mode) == "1":
            # Fetch the timespecific settings
            parameters = self._get_timeperiod_valuespec().from_html_vars(varprefix)
            if parameters[self.tp_values_key]:
                return parameters
            else:
                # Fall back to enclosed valuespec data when no timeperiod is set
                return parameters[self.tp_default_value_key]
        else:
            # Fetch the data from the enclosed valuespec
            return self._enclosed_valuespec.from_html_vars(varprefix)


    def canonical_value(self):
        return self._enclosed_valuespec.canonical_value()


    def validate_datatype(self, value, varprefix):
        if self._is_active(value):
            self._get_timeperiod_valuespec().validate_datatype(value, varprefix)
        else:
            self._enclosed_valuespec.validate_datatype(value, varprefix)


    def validate_value(self, value, varprefix):
        if self._is_active(value):
            self._get_timeperiod_valuespec().validate_value(value, varprefix)
        else:
            self._enclosed_valuespec.validate_value(value, varprefix)


    def _get_timeperiod_valuespec(self):
        return Dictionary(
                elements = [
                    (self.tp_values_key,
                        ListOf(
                            Tuple(
                                elements = [
                                    TimeperiodSelection(
                                        title = _("Match only during timeperiod"),
                                        help = _("Match this rule only during times where the "
                                                 "selected timeperiod from the monitoring "
                                                 "system is active."),
                                    ),
                                    self._enclosed_valuespec
                                ]
                            ),
                            title = _("Configured timeperiod parameters"),
                        )
                    ),
                    (self.tp_default_value_key,
                        Transform(
                            self._enclosed_valuespec,
                            title = _("Default parameters when no timeperiod matches")
                        )
                    ),
                ],
                optional_keys = False,
            )


    # Checks whether the tp-mode is switched on through the gui
    def _is_switched_on(self):
        return html.var(self.tp_toggle_var) == "1"


    # Checks whether the value itself already uses the tp-mode
    def _is_active(self, value):
        if isinstance(value, dict) and self.tp_default_value_key in value:
            return True
        else:
            return False


    # Returns simply the value or converts a plain value to a tp-value
    def _get_timeperiod_value(self, value):
        if isinstance(value, dict) and self.tp_default_value_key in value:
            return value
        else:
            return {self.tp_values_key: [], self.tp_default_value_key: value}


    # Returns simply the value or converts tp-value back to a plain value
    def _get_timeless_value(self, value):
        if isinstance(value, dict) and self.tp_default_value_key in value:
            return value.get(self.tp_default_value_key)
        else:
            return value



class CheckTypeGroupSelection(ElementSelection):
    def __init__(self, checkgroup, **kwargs):
        super(CheckTypeGroupSelection, self).__init__(**kwargs)
        self._checkgroup = checkgroup

    def get_elements(self):
        checks = watolib.check_mk_local_automation("get-check-information")
        elements = dict([ (cn, "%s - %s" % (cn, c["title"])) for (cn, c) in checks.items()
                     if c.get("group") == self._checkgroup ])
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
        title = _("Predictive Levels"),
        optional_keys = [ "weight", "levels_upper", "levels_upper_min", "levels_lower", "levels_lower_max" ],
        default_keys = [ "levels_upper" ],
        columns = 1,
        headers = "sup",
        elements = [
             ( "period",
                DropdownChoice(
                    title = _("Base prediction on"),
                    choices = [
                        ( "wday",   _("Day of the week (1-7, 1 is Monday)") ),
                        ( "day",    _("Day of the month (1-31)") ),
                        ( "hour",   _("Hour of the day (0-23)") ),
                        ( "minute", _("Minute of the hour (0-59)") ),
                    ]
             )),
             ( "horizon",
               Integer(
                   title = _("Time horizon"),
                   unit = _("days"),
                   minvalue = 1,
                   default_value = 90,
             )),
             # ( "weight",
             #   Percentage(
             #       title = _("Raise weight of recent time"),
             #       label = _("by"),
             #       default_value = 0,
             # )),
             ( "levels_upper",
               CascadingDropdown(
                   title = _("Dynamic levels - upper bound"),
                   choices = [
                       ( "absolute",
                         _("Absolute difference from prediction"),
                         Tuple(
                             elements = [
                                 Float(title = _("Warning at"),
                                       unit = unitname + _("above predicted value"), default_value = dif[0]),
                                 Float(title = _("Critical at"),
                                       unit = unitname + _("above predicted value"), default_value = dif[1]),
                             ]
                      )),
                      ( "relative",
                        _("Relative difference from prediction"),
                         Tuple(
                             elements = [
                                 Percentage(title = _("Warning at"), unit = _("% above predicted value"), default_value = 10),
                                 Percentage(title = _("Critical at"), unit = _("% above predicted value"), default_value = 20),
                             ]
                      )),
                      ( "stdev",
                        _("In relation to standard deviation"),
                         Tuple(
                             elements = [
                                 Percentage(title = _("Warning at"), unit = _("times the standard deviation above the predicted value"), default_value = 2),
                                 Percentage(title = _("Critical at"), unit = _("times the standard deviation above the predicted value"), default_value = 4),
                             ]
                      )),
                   ]
             )),
             ( "levels_upper_min",
                Tuple(
                    title = _("Limit for upper bound dynamic levels"),
                    help = _("Regardless of how the dynamic levels upper bound are computed according to the prediction: "
                             "the will never be set below the following limits. This avoids false alarms "
                             "during times where the predicted levels would be very low."),
                    elements = [
                        Float(title = _("Warning level is at least"), unit = unitname),
                        Float(title = _("Critical level is at least"), unit = unitname),
                    ]
              )),
             ( "levels_lower",
               CascadingDropdown(
                   title = _("Dynamic levels - lower bound"),
                   choices = [
                       ( "absolute",
                         _("Absolute difference from prediction"),
                         Tuple(
                             elements = [
                                 Float(title = _("Warning at"),
                                       unit = unitname + _("below predicted value"), default_value = 2.0),
                                 Float(title = _("Critical at"),
                                       unit = unitname + _("below predicted value"), default_value = 4.0),
                             ]
                      )),
                      ( "relative",
                        _("Relative difference from prediction"),
                         Tuple(
                             elements = [
                                 Percentage(title = _("Warning at"), unit = _("% below predicted value"), default_value = 10),
                                 Percentage(title = _("Critical at"), unit = _("% below predicted value"), default_value = 20),
                             ]
                      )),
                      ( "stdev",
                        _("In relation to standard deviation"),
                         Tuple(
                             elements = [
                                 Percentage(title = _("Warning at"), unit = _("times the standard deviation below the predicted value"), default_value = 2),
                                 Percentage(title = _("Critical at"), unit = _("times the standard deviation below the predicted value"), default_value = 4),
                             ]
                      )),
                   ]
             )),
        ]
    )


# To be used as ValueSpec for levels on numeric values, with
# prediction
def Levels(**kwargs):

    def match_levels_alternative(v):
        if type(v) == dict:
            return 2
        elif type(v) == tuple and v != (None, None):
            return 1
        else:
            return 0

    help = kwargs.get("help")
    unit = kwargs.get("unit")
    title = kwargs.get("title")
    default_levels = kwargs.get("default_levels", (0.0, 0.0))
    default_difference = kwargs.get("default_difference", (0,0))
    if "default_value" in kwargs:
        default_value = kwargs["default_value"]
    else:
        default_value = default_levels and default_levels or None

    return Alternative(
          title = title,
          help = help,
          show_titles = False,
          style = "dropdown",
          elements = [
              FixedValue(
                  None,
                  title = _("No Levels"),
                  totext = _("Do not impose levels, always be OK"),
              ),
              Tuple(
                  title = _("Fixed Levels"),
                  elements = [
                      Float(unit = unit, title = _("Warning at"), default_value = default_levels[0], allow_int = True),
                      Float(unit = unit, title = _("Critical at"), default_value = default_levels[1], allow_int = True),
                  ],
              ),
              PredictiveLevels(
                  default_difference = default_difference,
              ),
          ],
          match = match_levels_alternative,
          default_value = default_value,
    )


def may_edit_ruleset(varname):
    if varname == "ignored_services":
        return config.user.may("wato.services") or config.user.may("wato.rulesets")
    elif varname in [ "custom_checks", "datasource_programs" ]:
        return config.user.may("wato.rulesets") and config.user.may("wato.add_or_modify_executables")
    else:
        return config.user.may("wato.rulesets")


class CheckTypeSelection(DualListChoice):
    def __init__(self, **kwargs):
        super(CheckTypeSelection, self).__init__(rows=25, **kwargs)

    def get_elements(self):
        checks = watolib.check_mk_local_automation("get-check-information")
        elements = [ (cn, (cn + " - " + c["title"])[:60]) for (cn, c) in checks.items()]
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
                ( 'f', _("Start or end of flapping state")),
                ( 's', _("Start or end of a scheduled downtime")),
                ( 'x', _("Acknowledgement of problem")),
                ( 'as', _("Alert handler execution, successful")),
                ( 'af', _("Alert handler execution, failed")),
            ]
            add_default = [ 'f', 's', 'x', 'as', 'af' ]
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
              TimeperiodSelection(
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
        if html.has_var("_delete"):
            nr = int(html.var("_delete"))
            rule = rules[nr]
            c = wato_confirm(_("Confirm deletion of %s") % what_title,
                             _("Do you really want to delete the %s <b>%d</b> <i>%s</i>?") %
                               (what_title, nr, rule.get("description","")))
            if c:
                self._add_change(what + "-delete-rule", _("Deleted %s %d") % (what_title, nr))
                del rules[nr]
                save_rules(rules)
            elif c == False:
                return ""
            else:
                return

        elif html.has_var("_move"):
            if html.check_transaction():
                from_pos = html.get_integer_input("_move")
                to_pos = html.get_integer_input("_index")
                rule = rules[from_pos]
                del rules[from_pos] # make to_pos now match!
                rules[to_pos:to_pos] = [rule]
                save_rules(rules)
                self._add_change(what + "-move-rule",
                    _("Changed position of %s %d") % (what_title, from_pos))



# Sort given sites argument by local, followed by slaves
# TODO: Change to sorted() mechanism
def sort_sites(sitelist):
    def custom_sort(a,b):
        return cmp(a[1].get("replication"), b[1].get("replication")) or \
               cmp(a[1].get("alias"), b[1].get("alias"))
    sitelist.sort(cmp = custom_sort)
    return sitelist
