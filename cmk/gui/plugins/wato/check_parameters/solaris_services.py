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


def _valuespec_inventory_solaris_services_rules():
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
        help=_(
            'This rule can be used to configure the discovery of the Solaris services check. '
            'You can configure specific Solaris services to be monitored by the Solaris check by '
            'selecting them by description, category, name, or current state during the discovery.'
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name="inventory_solaris_services_rules",
        valuespec=_valuespec_inventory_solaris_services_rules,
    ))


def _parameter_valuespec_solaris_services():
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


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="solaris_services",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Name of the service"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_solaris_services,
        title=lambda: _("Solaris Services"),
    ))
