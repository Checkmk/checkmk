#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Defaults settings for global configuration

from collections.abc import Sequence
from typing import Literal

from cmk.utils.notify_types import EventRule

alert_handler_event_types: list[Literal["statechange", "checkresult"]] = ["statechange"]
alert_logging = 20
alert_handler_timeout = 60
alert_handler_rules: Sequence[EventRule] = []
