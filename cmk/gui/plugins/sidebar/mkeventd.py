#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Optional, Tuple

from livestatus import SiteId

import cmk.gui.mkeventd as mkeventd
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.htmllib.tag_rendering import HTMLContent
from cmk.gui.i18n import _
from cmk.gui.plugins.sidebar.utils import SidebarSnapin, snapin_registry, snapin_site_choice
from cmk.gui.type_defs import RoleName
from cmk.gui.user_sites import get_event_console_site_choices


@snapin_registry.register
class SidebarSnapinCustomers(SidebarSnapin):
    @staticmethod
    def type_name() -> str:
        return "mkeventd_performance"

    @classmethod
    def title(cls) -> str:
        return _("Event console performance")

    @classmethod
    def description(cls) -> str:
        return _("Monitor the performance of the Event Console")

    @classmethod
    def allowed_roles(cls) -> list[RoleName]:
        return ["admin"]

    @classmethod
    def refresh_regularly(cls) -> bool:
        return True

    def show(self) -> None:
        only_sites = snapin_site_choice("mkeventd_performance", get_event_console_site_choices())

        try:
            entries = self._mkeventd_performance_entries(only_sites)
        except Exception as e:
            html.show_error("%s" % e)
            return

        html.open_table(class_=["mkeventd_performance"])
        for _index, left, right in entries:
            html.tr(HTMLWriter.render_td("%s:" % left) + HTMLWriter.render_td(right))
        html.close_table()

    def _mkeventd_performance_entries(
        self, only_sites: Optional[List[SiteId]]
    ) -> List[Tuple[float, HTMLContent, HTMLContent]]:
        status = mkeventd.get_total_stats(only_sites)  # combination of several sites
        entries: List[Tuple[float, HTMLContent, HTMLContent]] = []

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
                (
                    3.5,
                    _("Rule hit ratio"),
                    "%.2f%%"
                    % (
                        status["status_average_rule_hit_rate"]
                        / status["status_average_rule_trie_rate"]
                        * 100
                    ),
                )
            )  # fixed: true-division

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
        entries.append(
            (
                6,
                "Processing load",
                "%.0f%%"
                % (
                    min(
                        100.0,
                        status["status_average_processing_time"]
                        * status["status_average_message_rate"]
                        * 100.0,
                    )
                ),
            )
        )

        return sorted(entries)
