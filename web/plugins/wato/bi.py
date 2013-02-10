#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

bi_aggregation_functions["worst"] = {
    "title"     : _("Worst - take worst of all node states"),
    "valuespec" : Tuple(
        elements = [
            Integer(
                help = _("Normally this value is <tt>1</tt>, which means that the worst state "
                         "of all child nodes is being used as the total state. If you set it for example "
                         "to <tt>2</tt>, then the node with the worst state is not being regarded. "
                         "If the states of the child nodes would be CRIT, WARN and OK, then to total "
                         "state would be WARN."),
                title = _("Take n'th worst state for n = "),
                default_value = 1,
                min_value = 1),
            MonitoringState(
                title = _("Restrict severity to at worst"),
                help = _("Here you can have the node the state WARN, even if some of the child nodes "
                         "are CRIT."),
                default_value = 2,
            ),
        ]),
}

bi_aggregation_functions["best"] = {
    "title"     : _("Best - take best of all node states"),
    "valuespec" : Tuple(
        elements = [
            Integer(
                help = _("Normally this value is <tt>1</tt>, which means that the best state "
                         "of all child nodes is being used as the total state. If you set it for example "
                         "to <tt>2</tt>, then the node with the best state is not being regarded. "
                         "If the states of the child nodes would be CRIT, WARN and OK, then to total "
                         "state would be WARN."),
                title = _("Take n'th best state for n = "),
                default_value = 1,
                min_value = 1),
            MonitoringState(
                title = _("Restrict severity to at worst "),
                help = _("Here you can have the node the state WARN, even if some of the child nodes "
                         "are CRIT."),
                default_value = 2,
            ),
        ]),
}

bi_aggregation_functions["count_ok"] = {
    "title"     : _("Count the number of nodes in state OK"),
    "valuespec" : Tuple(
        elements = [
            Integer(
                label = _("Required number of OK-nodes for a total state of OK:"),
                default_value = 2,
                min_value = 0),
            Integer(
                label = _("Required number of OK-nodes for a total state of WARN:"),
                default_value = 1,
                min_value = 0),
        ]),
}
