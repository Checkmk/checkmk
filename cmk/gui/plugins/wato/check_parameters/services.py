#!/usr/bin/python
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

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    ListOf,
    ListOfStrings,
    MonitoringState,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
    ABCHostValueRulespec,
    UserIconOrAction,
)


@rulespec_registry.register
class RulespecInventoryServicesRules(ABCHostValueRulespec):
    @property
    def group(self):
        return RulespecGroupCheckParametersDiscovery

    @property
    def name(self):
        return "inventory_services_rules"

    @property
    def match_type(self):
        return "all"

    @property
    def valuespec(self):
        return Dictionary(
            title=_("Windows Service Discovery"),
            elements=[
                ('services',
                 ListOfStrings(
                     title=_("Services (Regular Expressions)"),
                     help=_(
                         'Regular expressions matching the begining of the internal name '
                         'or the description of the service. '
                         'If no name is given then this rule will match all services. The '
                         'match is done on the <i>beginning</i> of the service name. It '
                         'is done <i>case sensitive</i>. You can do a case insensitive match '
                         'by prefixing the regular expression with <tt>(?i)</tt>. Example: '
                         '<tt>(?i).*mssql</tt> matches all services which contain <tt>MSSQL</tt> '
                         'or <tt>MsSQL</tt> or <tt>mssql</tt> or...'),
                     orientation="horizontal",
                 )),
                ('state',
                 DropdownChoice(
                     choices=[
                         ('running', _('Running')),
                         ('stopped', _('Stopped')),
                     ],
                     title=_("Create check if service is in state"),
                 )),
                ('start_mode',
                 DropdownChoice(
                     choices=[
                         ('auto', _('Automatic')),
                         ('demand', _('Manual')),
                         ('disabled', _('Disabled')),
                     ],
                     title=_("Create check if service is in start mode"),
                 )),
            ],
            help=_(
                'This rule can be used to configure the inventory of the windows services check. '
                'You can configure specific windows services to be monitored by the windows check by '
                'selecting them by name, current state during the inventory, or start mode.'),
        )


@rulespec_registry.register
class RulespecCheckgroupParametersServices(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "services"

    @property
    def title(self):
        return _("Windows Services")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ("additional_servicenames",
             ListOfStrings(
                 title=_("Alternative names for the service"),
                 help=_("Here you can specify alternative names that the service might have. "
                        "This helps when the exact spelling of the services can changed from "
                        "one version to another."),
             )),
            ("states",
             ListOf(
                 Tuple(orientation="horizontal",
                       elements=[
                           DropdownChoice(
                               title=_("Expected state"),
                               default_value="running",
                               choices=[(None, _("ignore the state")), ("running", _("running")),
                                        ("stopped", _("stopped"))],
                           ),
                           DropdownChoice(
                               title=_("Start type"),
                               default_value="auto",
                               choices=[
                                   (None, _("ignore the start type")),
                                   ("demand", _("demand")),
                                   ("disabled", _("disabled")),
                                   ("auto", _("auto")),
                                   ("unknown", _("unknown (old agent)")),
                               ],
                           ),
                           MonitoringState(title=_("Resulting state"),),
                       ],
                       default_value=("running", "auto", 0)),
                 title=_("Services states"),
                 help=_("You can specify a separate monitoring state for each possible "
                        "combination of service state and start type. If you do not use "
                        "this parameter, then only running/auto will be assumed to be OK."),
             )), (
                 "else",
                 MonitoringState(
                     title=_("State if no entry matches"),
                     default_value=2,
                 ),
             ),
            ('icon',
             UserIconOrAction(
                 title=_("Add custom icon or action"),
                 help=_("You can assign icons or actions to the found services in the status GUI."),
             ))
        ],)

    @property
    def item_spec(self):
        return TextAscii(title=_("Name of the service"),
                         help=_(
                             "Please Please note, that the agent replaces spaces in "
                             "the service names with underscores. If you are unsure about the "
                             "correct spelling of the name then please look at the output of "
                             "the agent (cmk -d HOSTNAME). The service names  are in the first "
                             "column of the section &lt;&lt;&lt;services&gt;&gt;&gt;. Please "
                             "do not mix up the service name with the display name of the service."
                             "The latter one is just being displayed as a further information."),
                         allow_empty=False)
