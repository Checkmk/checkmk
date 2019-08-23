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

import cmk.utils.paths
import cmk.utils.defines as defines

from cmk.gui.valuespec import (
    DualListChoice,
    Age,
    Dictionary,
    Transform,
    DropdownChoice,
    TextAscii,
    MonitoringState,
)
from cmk.gui.i18n import _

from cmk.gui.plugins.wato import (
    rulespec_group_registry,
    RulespecGroup,
    rulespec_registry,
    ABCHostValueRulespec,
)


@rulespec_group_registry.register
class RulespecGroupInventory(RulespecGroup):
    @property
    def name(self):
        return "inventory"

    @property
    def title(self):
        return _("Hardware / Software Inventory")

    @property
    def help(self):
        return _("Configuration of the Check_MK Hardware and Software Inventory System")


@rulespec_registry.register
class RulespecActiveChecksCmkInv(ABCHostValueRulespec):
    @property
    def group(self):
        return RulespecGroupInventory

    @property
    def name(self):
        return "active_checks:cmk_inv"

    @property
    def match_type(self):
        return "all"

    @property
    def valuespec(self):
        return Transform(
            Dictionary(elements=[
                ("sw_changes",
                 MonitoringState(
                     title=_("State when software changes are detected"),
                     default_value=0,
                 )),
                ("sw_missing",
                 MonitoringState(
                     title=_("State when software packages info is missing"),
                     default_value=0,
                 )),
                ("hw_changes",
                 MonitoringState(
                     title=_("State when hardware changes are detected"),
                     default_value=0,
                 )),
                ("fail_status",
                 MonitoringState(
                     title=_("State when inventory fails"),
                     help=_("The check takes this state in case the inventory cannot be "
                            "updated because of any possible reason. A common use is "
                            "setting this to OK for workstations that can be switched "
                            "off - so you will get no notifications in that case."),
                     default_value=1,
                 )),
                ("status_data_inventory",
                 DropdownChoice(
                     title=_("Status data inventory"),
                     help=_("All hosts configured via this ruleset will do a hardware and "
                            "software inventory after every check cycle if there's at least "
                            "one inventory plugin which processes status data. "
                            "<b>Note:</b> in order to get any useful "
                            "result for agent based hosts make sure that you have installed "
                            "the agent plugin <tt>mk_inventory</tt> on these hosts."),
                     choices=[
                         (True, _("Do status data inventory")),
                         (False, _("Do not status data inventory")),
                     ],
                     default_value=True,
                 )),
            ]),
            title=_("Do hardware/software Inventory"),
            help=_("All hosts configured via this ruleset will do a hardware and "
                   "software inventory. For each configured host a new active check "
                   "will be created. You should also create a rule for changing the "
                   "normal interval for that check to something between a couple of "
                   "hours and one day. "
                   "<b>Note:</b> in order to get any useful "
                   "result for agent based hosts make sure that you have installed "
                   "the agent plugin <tt>mk_inventory</tt> on these hosts."),
            forth=lambda x: x is not None and x or {},  # convert from legacy None
        )


@rulespec_registry.register
class RulespecInvExportsSoftwareCsv(ABCHostValueRulespec):
    @property
    def group(self):
        return RulespecGroupInventory

    @property
    def name(self):
        return "inv_exports:software_csv"

    @property
    def valuespec(self):
        return Dictionary(
            title=_("Export List of Software packages as CSV file"),
            elements=[
                ("filename",
                 TextAscii(
                     title=_(
                         "Export file to create, containing <tt>&ly;HOST&gt;</tt> for the hostname"
                     ),
                     help=
                     _("Please specify the path to the export file. The text <tt>&lt;HOST&gt;</tt> "
                       "will be replaced with the host name the inventory has been done for. "
                       "If you use a relative path then that will be relative to Check_MK's directory "
                       "for variable data, which is <tt>%s</tt>.") % cmk.utils.paths.var_dir,
                     allow_empty=False,
                     size=64,
                     default_value="csv-export/<HOST>.csv",
                 )),
                ("separator",
                 TextAscii(
                     title=_("Separator"),
                     allow_empty=False,
                     size=1,
                     default_value=";",
                 )),
                ("quotes",
                 DropdownChoice(
                     title=_("Quoting"),
                     choices=[
                         (None, _("Don't use quotes")),
                         ("single", _("Use single quotes, escape contained quotes with backslash")),
                         ("double", _("Use double quotes, escape contained quotes with backslash")),
                     ],
                     default_value=None,
                 )),
                ("headers",
                 DropdownChoice(
                     title=_("Column headers"),
                     choices=[
                         (False, _("Do not add column headers")),
                         (True, _("Add a first row with column titles")),
                     ],
                     default_value=False,
                 )),
            ],
            required_keys=["filename"],
        )


@rulespec_registry.register
class RulespecInvParametersInvIf(ABCHostValueRulespec):
    @property
    def group(self):
        return RulespecGroupInventory

    @property
    def name(self):
        return "inv_parameters:inv_if"

    @property
    def match_type(self):
        return "dict"

    @property
    def valuespec(self):
        return Dictionary(
            title=_("Parameters for switch port inventory"),
            elements=[
                ("unused_duration",
                 Age(
                     title=_("Port down time until considered unused"),
                     help=_(
                         "After this time in the state <i>down</i> a port is considered unused."),
                     default_value=30 * 86400,
                 )),
                ("usage_port_types",
                 DualListChoice(
                     title=_("Port types to include in usage statistics"),
                     choices=defines.interface_port_types(),
                     autoheight=False,
                     rows=40,
                     enlarge_active=False,
                     custom_order=True,
                     default_value=[
                         '6', '32', '62', '117', '127', '128', '129', '180', '181', '182', '205',
                         '229'
                     ],
                 )),
            ])
