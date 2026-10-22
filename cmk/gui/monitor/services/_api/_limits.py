#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Final

from cmk.gui.logged_in import LoggedInUser

# View-local limits, deliberately not coupled to the global soft/hard query limit settings so they
# never affect the legacy views. Shared by every service listing so their row limits can't drift
# apart.
MIN_SERVICE_LIMIT: Final = 0
MAX_SERVICE_LIMIT: Final = 5_000
DEFAULT_SERVICE_LIMIT: Final = 1_000

# The row limits the service pages offer: the default first, the maximum last.
LIMIT_TIERS: Final = (DEFAULT_SERVICE_LIMIT, MAX_SERVICE_LIMIT)


def resolve_service_limit(requested: int | None, user: LoggedInUser) -> int | None:
    # A `None` request means "remove the limit". We only honor that for users allowed to ignore
    # the hard limit; everyone else is clamped to the safety ceiling. Numeric requests are
    # already bounded to the ceiling by the request schema, so they pass through unchanged.
    match requested:
        case None if user.may("general.ignore_hard_limit"):
            return None
        case None:
            return MAX_SERVICE_LIMIT
        case _:
            return requested
