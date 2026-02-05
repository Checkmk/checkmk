#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"

import time
from typing import NamedTuple

from livestatus import MKLivestatusNotFoundError

from cmk.ccc.exceptions import MKGeneralException, MKTimeout
from cmk.gui import sites
from cmk.gui.config import active_config
from cmk.gui.ctx_stack import g
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
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

g_columns: list[str] = [
    "time",
    "contact_name",
    "command_name",
    "host_name",
    "service_description",
    "comment",
]


class FailedNotificationTimes(NamedTuple):
    acknowledged_unitl: float
    modified: float


def get_disabled_notifications_infos() -> tuple[int, list[str]]:
    query_str = "GET status\nColumns: enable_notifications\n"
    with prepend_site():
        notification_status = live().query(query_str)
    sites_with_disabled_notifications = []
    for status in notification_status:
        if status[1] == 0:
            sites_with_disabled_notifications.append(status[0])

    return len(notification_status), sites_with_disabled_notifications


def acknowledged_time() -> float:
    """Returns the timestamp to start looking for failed notifications for the current user"""
    times: FailedNotificationTimes | None = g.get("failed_notification_times")

    # Initialize the request cache "g.failed_notification_times" from the user profile in case it is
    # needed. Either on first call to this function or when the file on disk was modified.
    if times is None or user.file_modified("acknowledged_notifications") > times.modified:
        now = time.time()
        user_time = user.acknowledged_notifications

        if user_time == 0:
            # When this timestamp is first initialized, save the current timestamp as the
            # acknowledge date. This should considerably reduce the number of log files that have to
            # be searched when retrieving the list
            acknowledge_failed_notifications(now, now)
        else:
            g.failed_notification_times = FailedNotificationTimes(
                user.acknowledged_notifications, now
            )

    return g.failed_notification_times.acknowledged_unitl


def number_of_failed_notifications(from_timestamp: float) -> int:
    if not may_see_failed_notifications():
        return 0

    query_txt = failed_notification_query(
        before=None, after=from_timestamp, extra_headers=None, stat_only=True
    )

    try:
        result: int = sites.live().query_summed_stats(query_txt)[0]
    except MKLivestatusNotFoundError:
        result = 0  # Normalize the result when no site answered

    if result == 0 and not sites.live().dead_sites():
        # In case there are no errors and all sites are reachable:
        # advance the users acknowledgement time
        now = time.time()
        acknowledge_failed_notifications(now, now)

    return result


def number_of_total_sent_notifications(from_timestamp: float) -> int:
    query = (
        "GET log\n"
        "Stats: class = 3\n"
        f"Filter: log_time >= {from_timestamp}\n"
        "Filter: log_type ~~ .*NOTIFICATION RESULT$\n"
        # do not show internal notification events (just end user notifications)
        "Filter: log_command_name != check-mk-notify\n"
    )
    try:
        send_per_site_list = sites.live().query(query)
    except MKTimeout:
        raise
    except Exception as exc:
        raise MKGeneralException(_("The query returned no data.")) from exc

    if not send_per_site_list:
        return 0

    return sum(sum(site) for site in send_per_site_list)


def effective_notification_horizon(with_acknowledgement: bool) -> float:
    """Returns the effective notification horizon in seconds for the current user,
    taking into account the time since last acknowledgement if requested.
    """
    return max(
        acknowledged_time() if with_acknowledgement else 0,
        time.time()
        - (
            active_config.failed_notification_horizon
            if user.may("general.see_failed_notifications")
            else 86400
        ),
    )


def failed_notification_query(
    before: float | None,
    after: float,
    extra_headers: str | None = None,
    *,
    stat_only: bool,
) -> str:
    query = ["GET log"]
    if stat_only:
        query.append("Stats: log_state != 0")
    else:
        query.append("Columns: %s" % " ".join(g_columns))
        query.append("Filter: log_state != 0")

    query.extend(
        [
            "Filter: class = 3",
            "Filter: log_type = SERVICE NOTIFICATION RESULT",
            "Filter: log_type = HOST NOTIFICATION RESULT",
            "Or: 2",
            "Filter: time >= %d" % after,
        ]
    )

    if before is not None:
        query.append("Filter: time <= %d" % before)

    query_txt = "\n".join(query)

    if extra_headers is not None:
        query_txt += extra_headers

    return query_txt


def may_see_failed_notifications() -> bool:
    return user.may("general.see_failed_notifications") or user.may(
        "general.see_failed_notifications_24h"
    )


def acknowledge_failed_notifications(timestamp: float, now: float) -> None:
    """Set the acknowledgement time for the current user"""
    g.failed_notification_times = FailedNotificationTimes(timestamp, now)
    user.acknowledged_notifications = int(timestamp)
