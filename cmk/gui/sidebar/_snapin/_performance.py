#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui import site_config, sites, user_sites
from cmk.gui.config import Config
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.type_defs import RoleName

from ._base import SidebarSnapin
from ._helpers import snapin_site_choice


class Performance(SidebarSnapin):
    @staticmethod
    def type_name() -> str:
        return "performance"

    @classmethod
    def title(cls) -> str:
        return _("Server performance")

    @classmethod
    def has_show_more_items(cls) -> bool:
        return True

    @classmethod
    def description(cls) -> str:
        return _("Live monitor of the overall performance of all monitoring servers")

    @classmethod
    def refresh_regularly(cls) -> bool:
        return True

    def show(self, config: Config) -> None:
        only_sites = snapin_site_choice("performance", user_sites.get_configured_site_choices())

        def write_line(left, right, show_more):
            html.open_tr(class_="show_more_mode" if show_more else "basic")
            html.td(left, class_="left")
            html.td(HTMLWriter.render_strong(right), class_="right")
            html.close_tr()

        html.open_table(class_=["performance"])

        try:
            sites.live().set_only_sites(only_sites)
            data = sites.live().query(
                "GET status\nColumns: service_checks_rate host_checks_rate "
                "external_commands_rate connections_rate forks_rate "
                "log_messages_rate cached_log_messages "
                "carbon_overflows_rate carbon_queue_usage carbon_bytes_sent_rate "
                "influxdb_overflows_rate influxdb_queue_usage influxdb_bytes_sent_rate "
                "rrdcached_overflows_rate rrdcached_queue_usage rrdcached_bytes_sent_rate\n"
            )
        finally:
            sites.live().set_only_sites(None)

        for what, show_more, col, format_str in [
            ("Service checks", False, 0, "%.2f/s"),
            ("Host checks", False, 1, "%.2f/s"),
            ("External commands", True, 2, "%.2f/s"),
            ("Livestatus-conn.", True, 3, "%.2f/s"),
            ("Process creations", True, 4, "%.2f/s"),
            ("New log messages", True, 5, "%.2f/s"),
            ("Cached log messages", True, 6, "%d"),
            ("Carbon overflow rate", True, 7, "%d/s"),
            ("Carbon queue usage", True, 8, "%.2f %%"),
            ("Carbon I/O", True, 9, "%d bytes/s"),
            ("InfluxDB overflow rate", True, 10, "%d/s"),
            ("InfluxDB queue usage", True, 11, "%.2f %%"),
            ("InfluxDB I/O", True, 12, "%d bytes/s"),
            ("RRD overflow rate", True, 13, "%d/s"),
            ("RRD queue usage", True, 14, "%.2f %%"),
            ("RRD I/O", True, 15, "%d bytes/s"),
        ]:
            write_line(what + ":", format_str % sum(row[col] for row in data), show_more=show_more)

        if only_sites is None and len(site_config.enabled_sites()) == 1:
            try:
                data = sites.live().query(
                    "GET status\nColumns: external_command_buffer_slots "
                    "external_command_buffer_max\n"
                )
            finally:
                sites.live().set_only_sites(None)
            size = sum(row[0] for row in data)
            maxx = sum(row[1] for row in data)
            write_line(_("Com. buf. max/total"), "%d / %d" % (maxx, size), show_more=True)

        html.close_table()

    @classmethod
    def refresh_on_restart(cls) -> bool:
        return True

    @classmethod
    def allowed_roles(cls) -> list[RoleName]:
        return [
            "admin",
        ]
