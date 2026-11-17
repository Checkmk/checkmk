#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

RELAY_LABEL_KEY = "cmk/relay"

_ACTIVE_CHECK_TYPE = 0


def is_scheduled_by_relay(
    *, next_check: float, check_type: int, host_labels: Mapping[str, str]
) -> bool:
    """A relay schedules the active checks it runs, so the core reports no next check."""
    return not next_check and check_type == _ACTIVE_CHECK_TYPE and RELAY_LABEL_KEY in host_labels
