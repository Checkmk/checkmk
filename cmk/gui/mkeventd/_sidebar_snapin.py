#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator

from livestatus import MKLivestatusBadGatewayError, MKLivestatusTableNotFoundError, OnlySites, Query

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.config import Config
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.htmllib.tag_rendering import HTMLContent
from cmk.gui.i18n import _
from cmk.gui.sidebar import SidebarSnapin, snapin_site_choice
from cmk.gui.type_defs import RoleName
from cmk.gui.user_sites import get_event_console_site_choices


class SidebarSnapinEventConsole(SidebarSnapin):
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

    def show(self, config: Config) -> None:
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
        self, only_sites: list[SiteId] | None
    ) -> list[tuple[float, HTMLContent, HTMLContent]]:
        status = get_total_stats(only_sites)  # combination of several sites
        entries: list[tuple[float, HTMLContent, HTMLContent]] = []

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


def get_total_stats(only_sites: OnlySites) -> dict[str, float]:
    stats_per_site = list(get_stats_per_site(only_sites))

    # First simply add rates. Times must then be averaged
    # weighted by message rate or connect rate
    total_stats: dict[str, float] = {}
    for row in stats_per_site:
        for key, value in row.items():
            if key.endswith("rate"):
                total_stats.setdefault(key, 0.0)
                total_stats[key] += value
    if not total_stats:
        if only_sites is None:
            raise MKGeneralException(_("Got no data from any site"))
        raise MKGeneralException(_("Got no data from this site"))

    for row in stats_per_site:
        for time_key, in_relation_to in [
            ("status_average_processing_time", "status_average_message_rate"),
            ("status_average_request_time", "status_average_connect_rate"),
        ]:
            total_stats.setdefault(time_key, 0.0)
            if total_stats[in_relation_to]:  # avoid division by zero
                my_weight = (
                    row[in_relation_to] / total_stats[in_relation_to]
                )  # fixed: true-division
                total_stats[time_key] += my_weight * row[time_key]

    total_sync_time = 0.0
    count = 0
    for row in stats_per_site:
        if row["status_average_sync_time"] > 0.0:
            count += 1
            total_sync_time += row["status_average_sync_time"]

    if count > 0:
        total_stats["status_average_sync_time"] = total_sync_time / count  # fixed: true-division

    return total_stats


def get_stats_per_site(only_sites: OnlySites) -> Iterator[dict[str, float]]:
    stats_keys = [
        "status_average_message_rate",
        "status_average_rule_trie_rate",
        "status_average_rule_hit_rate",
        "status_average_event_rate",
        "status_average_connect_rate",
        "status_average_overflow_rate",
        "status_average_rule_trie_rate",
        "status_average_rule_hit_rate",
        "status_average_processing_time",
        "status_average_request_time",
        "status_average_sync_time",
    ]
    try:
        sites.live().set_only_sites(only_sites)
        # Do not mark the site as dead in case the Event Console is not available.
        query = Query(
            "GET eventconsolestatus\nColumns: %s" % " ".join(stats_keys),
            suppress_exceptions=(MKLivestatusTableNotFoundError, MKLivestatusBadGatewayError),
        )
        for list_row in sites.live().query(query):
            yield dict(zip(stats_keys, list_row))
    finally:
        sites.live().set_only_sites(None)
