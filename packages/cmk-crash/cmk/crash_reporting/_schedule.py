#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import random
from datetime import timedelta
from logging import getLogger
from pathlib import Path

from cmk.ccc import store

logger = getLogger("cmk.crash_reporting.schedule")

_UPLOAD_INTERVAL = timedelta(days=1).total_seconds()

# Quantised by the cron period: 2h over 30-min ticks is four slots, not a continuum.
_FIRST_RUN_SPREAD = timedelta(hours=2).total_seconds()


def claim_due_run(omd_root: Path, now: float) -> bool:
    """Return True at most once per upload interval.

    The next run is stored before the caller uploads, so a cron tick overlapping a
    still-running batch sees "not due" and exits.
    """
    state_file = omd_root / "var/check_mk/crash_upload_next_run"
    with store.locked(state_file):
        try:
            due_at: int | None = int(store.load_text_from_file(state_file, default=""))
        except ValueError:
            due_at = None

        # A point further out than one interval can only come from a restored backup or a
        # clock jump ahead. Nothing else rearms, so a bad value wedges uploads until then.
        if due_at is None or due_at > now + _UPLOAD_INTERVAL:
            store.save_text_to_file(
                state_file, str(int(now + random.uniform(0, _FIRST_RUN_SPREAD)))
            )
            return False

        if now < due_at:
            logger.debug("Crash upload not due before %(due_at)s", {"due_at": due_at})
            return False

        # One interval from the due point, not from now: the tick that observes it lands up
        # to 30 min late, and anchoring on the tick would push the slot later every day.
        next_due = due_at + int(_UPLOAD_INTERVAL)
        if next_due <= now:
            # Down for a day or more: resume from now instead of one run per missed tick.
            next_due = int(now + _UPLOAD_INTERVAL)
        store.save_text_to_file(state_file, str(next_due))

    return True
