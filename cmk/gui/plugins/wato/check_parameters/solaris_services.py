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
    Alternative,
    Dictionary,
    DropdownChoice,
    FixedValue,
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
    HostRulespec,
)


@rulespec_registry.register
class RulespecInventorySolarisServicesRules(HostRulespec):
    @property
    def group(self):
        return RulespecGroupCheckParametersDiscovery

    @property
    def name(self):
        return "inventory_solaris_services_rules"

    @property
    def match_type(self):
        return "all"

    @property
    def valuespec(self):
        return Dictionary(
            title=_("Solaris Service Discovery"),
            elements=[
                ('descriptions', ListOfStrings(title=_("Descriptions"))),
                ('categories', ListOfStrings(title=_("Categories"))),
                ('names', ListOfStrings(title=_("Names"))),
                ('instances', ListOfStrings(title=_("Instances"))),
                ('states',
                 ListOf(
                     DropdownChoice(choices=[
                         ("online", _("online")),
                         ("disabled", _("disabled")),
                         ("maintenance", _("maintenance")),
                         ("legacy_run", _("legacy run")),
                     ],),
                     title=_("States"),
                 )),
                ('outcome',
                 Alternative(
                     title=_("Service name"),
                     style="dropdown",
                     elements=[
                         FixedValue("full_descr", title=_("Full Description"), totext=""),
                         FixedValue("descr_without_prefix",
                                    title=_("Description without type prefix"),
                                    totext=""),
                     ],
                 )),
            ],
            help=
            _('This rule can be used to configure the discovery of the Solaris services check. '
              'You can configure specific Solaris services to be monitored by the Solaris check by '
              'selecting them by description, category, name, or current state during the discovery.'
             ),
        )


@rulespec_registry.register
class RulespecCheckgroupParametersSolarisServices(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "solaris_services"

    @property
    def title(self):
        return _("Solaris Services")

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
                 Tuple(
                     orientation="horizontal",
                     elements=[
                         DropdownChoice(
                             title=_("Expected state"),
                             choices=[
                                 (None, _("Ignore the state")),
                                 ("online", _("Online")),
                                 ("disabled", _("Disabled")),
                                 ("maintenance", _("Maintenance")),
                                 ("legacy_run", _("Legacy run")),
                             ],
                         ),
                         DropdownChoice(
                             title=_("STIME"),
                             choices=[
                                 (None, _("Ignore")),
                                 (True, _("Has changed")),
                                 (False, _("Did not changed")),
                             ],
                         ),
                         MonitoringState(title=_("Resulting state"),),
                     ],
                 ),
                 title=_("Services states"),
                 help=_("You can specify a separate monitoring state for each possible "
                        "combination of service state. If you do not use this parameter, "
                        "then only online/legacy_run will be assumed to be OK."),
             )),
            ("else", MonitoringState(
                title=_("State if no entry matches"),
                default_value=2,
            )),
        ],)

    @property
    def item_spec(self):
        return TextAscii(title=_("Name of the service"), allow_empty=False)
