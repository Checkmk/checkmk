#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""What every page that offers a service may do with it, in one place."""

SERVICE_SUPPORTED_ACTIONS: tuple[str, ...] = (
    "acknowledge",
    "reschedule",
    "schedule_downtimes",
    "remove_acknowledgments",
    "remove_downtimes_hosts_services",
    "send_custom_notification",
    "add_comment",
    "fake_check_result",
)
