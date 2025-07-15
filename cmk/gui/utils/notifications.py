#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.exceptions import MKGeneralException, MKTimeout

from cmk.gui.i18n import _
from cmk.gui.notifications import acknowledged_time, number_of_failed_notifications
from cmk.gui.sites import live, prepend_site

OPTIMIZE_NOTIFICATIONS_ENTRIES: dict[str, list[str]] = {
    _("Balance short-term spikes"): [
        "extra_host_conf:first_notification_delay",
        "extra_service_conf:first_notification_delay",
        "cmc_host_flap_settings",
        "cmc_service_flap_settings",
        "extra_host_conf:max_check_attempts",
        "extra_service_conf:max_check_attempts",
    ],
    _("Restrict generation of notifications"): [
        "extra_host_conf:notifications_enabled",
        "extra_service_conf:notifications_enabled",
        "extra_host_conf:notification_options",
        "extra_service_conf:notification_options",
    ],
    _("Monitor"): [
        "active_checks:notify_count",
    ],
}

SUPPORT_NOTIFICATIONS_ENTRIES: dict[str, list[str]] = {
    _("Escalations"): [
        "extra_host_conf:notification_interval",
        "extra_service_conf:notification_interval",
    ],
    _("Time dependencies"): [
        "extra_host_conf:notification_period",
        "extra_service_conf:notification_period",
    ],
    _("Contact groups"): [
        "host_contactgroups",
        "service_contactgroups",
    ],
}


def get_disabled_notifications_infos() -> tuple[int, list[str]]:
    query_str = "GET status\nColumns: enable_notifications\n"
    with prepend_site():
        notification_status = live().query(query_str)
    sites_with_disabled_notifications = []
    for status in notification_status:
        if status[1] == 0:
            sites_with_disabled_notifications.append(status[0])

    return len(notification_status), sites_with_disabled_notifications


def get_failed_notification_count() -> int:
    return number_of_failed_notifications(after=acknowledged_time())


def get_total_sent_notifications(from_timestamp: int) -> int:
    query = (
        "GET log\n"
        "Stats: class = 3\n"
        f"Filter: log_time >= {from_timestamp}\n"
        "Filter: log_type ~~ .*NOTIFICATION RESULT$\n"
        # do not show internal notification events (just end user notifications)
        "Filter: log_command_name != check-mk-notify\n"
    )
    try:
        send_per_site_list = live().query(query)
    except MKTimeout:
        raise
    except Exception as exc:
        raise MKGeneralException(_("The query returned no data.")) from exc

    if not send_per_site_list:
        return 0

    return sum(sum(site) for site in send_per_site_list)
