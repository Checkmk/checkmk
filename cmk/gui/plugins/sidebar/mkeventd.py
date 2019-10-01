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

from __future__ import division
import cmk.gui.mkeventd as mkeventd
import cmk.gui.config as config
from cmk.gui.i18n import _
from cmk.gui.globals import html

from cmk.gui.plugins.sidebar import (
    snapin_site_choice,
    SidebarSnapin,
    snapin_registry,
)


@snapin_registry.register
class SidebarSnapinCustomers(SidebarSnapin):
    @staticmethod
    def type_name():
        return "mkeventd_performance"

    @classmethod
    def title(cls):
        return _("Event Console Performance")

    @classmethod
    def description(cls):
        return _("Monitor the performance of the Event Console")

    @classmethod
    def allowed_roles(cls):
        return ["admin"]

    @classmethod
    def refresh_regularly(cls):
        return True

    def show(self):
        only_sites = snapin_site_choice("mkeventd_performance",
                                        config.get_event_console_site_choices())

        try:
            entries = self._mkeventd_performance_entries(only_sites)
        except Exception as e:
            html.show_error(e)
            return

        html.open_table(class_=["mkeventd_performance"])
        for _index, left, right in entries:
            html.tr(html.render_td("%s:" % left) + html.render_td(right))
        html.close_table()

    def _mkeventd_performance_entries(self, only_sites):
        status = mkeventd.get_total_stats(only_sites)  # combination of several sites
        entries = []

        # TODO: Reorder these values and create a useful order.
        # e.g. Client connects and Time per client request after
        # each other.
        columns = [
            (1, _("Received messages"), "message", "%.2f/s"),
            (2, _("Rule tries"), "rule_trie", "%.2f/s"),
            (3, _("Rule hits"), "rule_hit", "%.2f/s"),
            (4, _("Created events"), "event", "%.2f/s"),
            (10, _("Client connects"), "connect", "%.2f/s"),
            (9, _("Overflows"), "overflow", "%.2f/s"),
        ]
        for index, what, col, fmt in columns:
            col_name = "status_average_%s_rate" % col
            if col_name in status:
                entries.append((index, what, fmt % status[col_name]))

        # Hit rate
        if status["status_average_rule_trie_rate"] == 0.0:
            entries.append((3.5, _("Rule hit ratio"), _("-.-- %")))
        else:
            entries.append(
                (3.5, _("Rule hit ratio"), "%.2f%%" %
                 (status["status_average_rule_hit_rate"] / status["status_average_rule_trie_rate"] *
                  100)))  # fixed: true-division

        # Time columns
        time_columns = [
            (5, _("Processing time per message"), "processing"),
            (11, _("Time per client request"), "request"),
            (20, _("Replication synchronization"), "sync"),
        ]
        for index, title, name in time_columns:
            value = status.get("status_average_%s_time" % name)
            if value:
                entries.append((index, title, "%.3f ms" % (value * 1000)))
            elif name != "sync":
                entries.append((index, title, _("-.-- ms")))

        # Load
        entries.append((6, "Processing load", "%.0f%%" % (min(
            100.0, status["status_average_processing_time"] *
            status["status_average_message_rate"] * 100.0))))

        entries.sort()
        return entries
