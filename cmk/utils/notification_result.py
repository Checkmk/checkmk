#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NewType, TypedDict

# 0 -> OK
# 1 -> temporary issue
# 2 -> permanent issue
NotificationResultCode = NewType("NotificationResultCode", int)
NotificationPluginName = NewType("NotificationPluginName", str)

NotificationContext = NewType("NotificationContext", dict[str, str])


class NotificationResult(TypedDict, total=False):
    plugin: NotificationPluginName
    status: NotificationResultCode
    output: list[str]
    forward: bool
    context: NotificationContext
