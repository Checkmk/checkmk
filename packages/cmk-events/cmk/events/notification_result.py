#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NewType, TypedDict

NOTIFICATION_RESULT_OK = 0
NOTIFICATION_RESULT_TEMPORARY_ISSUE = 1
NOTIFICATION_RESULT_PERMANENT_ISSUE = 2

NotificationResultCode = NewType("NotificationResultCode", int)
NotificationPluginName = NewType("NotificationPluginName", str)

NotificationContext = NewType("NotificationContext", dict[str, str])


class NotificationResult(TypedDict, total=False):
    plugin: NotificationPluginName
    status: NotificationResultCode
    output: list[str]
    forward: bool
    context: NotificationContext
