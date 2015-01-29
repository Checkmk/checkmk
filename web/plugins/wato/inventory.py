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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

register_rulegroup("inventory",
    _("Hardware/Software-Inventory"),
    _("Configuration of the Check_MK Hardware and Software Inventory System"))
group = "inventory"

register_rule(group,
    "active_checks:cmk_inv",
    Transform(
        Dictionary(
            elements = [
                ( "sw_changes",
                  MonitoringState(
                      title = _("State when software changes are detected"),
                      default_value = 0,
                )),
                ( "hw_changes",
                  MonitoringState(
                      title = _("State when hardware changes are detected"),
                      default_value = 0,
                )),
            ]
        ),
        title = _("Do hardware/software Inventory"),
        help = _("All hosts configured via this ruleset will do a hardware and "
               "software inventory. For each configured host a new active check "
               "will be created. You should also create a rule for changing the "
               "normal interval for that check to something between a couple of "
               "hours and one day. "
               "<b>Note:</b> in order to get any useful "
               "result for agent based hosts make sure that you have installed "
               "the agent plugin <tt>mk_inventory</tt> on these hosts."),
        forth = lambda x: { }, # convert from legacy None
    ),
    match = "all",
)

register_rule(group,
    "inv_exports:software_csv",
    Dictionary(
        title = _("Export List of Software packages as CSV file"),
        elements = [
            ( "filename",
              TextAscii(
                  title = _("Export file to create, containing <tt>&lt;HOST&gt;</tt> for the hostname"),
                  help = _("Please specify the path to the export file. The text <tt>&lt;HOST&gt;</tt> "
                           "will be replaced with the host name the inventory has been done for. "
                           "If you use a relative path then that will be relative to Check_MK's directory "
                           "for variable data, which is <tt>%s</tt>.") % defaults.var_dir,
                  allow_empty = False,
                  size = 64,
                  default_value = "csv-export/<HOST>.csv",
              )),
            ( "separator",
              TextAscii(
                  title = _("Separator"),
                  allow_empty = False,
                  size = 1,
                  default_value = ";",
            )),
            ( "quotes",
              DropdownChoice(
                  title = _("Quoting"),
                  choices = [
                    ( None, _("Don't use quotes") ),
                    ( "single", _("Use single quotes, escape contained quotes with backslash") ),
                    ( "double", _("Use double quotes, escape contained quotes with backslash") ),
                 ],
                 default_value = None,
            )),
            ( "headers",
              DropdownChoice(
                  title = _("Column headers"),
                  choices = [
                    ( False, _("Do not add column headers") ),
                    ( True, _("Add a first row with column titles") ),
                  ],
                  default_value = False,
            )),
        ],
        required_keys = [ "filename" ],
    ),
    match = "first"
)
